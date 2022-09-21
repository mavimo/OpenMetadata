#  Copyright 2021 Collate
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#  http://www.apache.org/licenses/LICENSE-2.0
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import types
import unittest
from typing import Optional
from unittest import TestCase
from unittest.mock import patch

from google.cloud.bigquery import (
    Client,
    PartitionRange,
    RangePartitioning,
    TimePartitioning,
)
from google.cloud.bigquery.table import Table
from pydantic import BaseModel, Extra

from metadata.generated.schema.entity.data.database import Database
from metadata.generated.schema.entity.data.table import IntervalType
from metadata.generated.schema.metadataIngestion.workflow import (
    OpenMetadataWorkflowConfig,
)
from metadata.generated.schema.type.entityReference import EntityReference
from metadata.ingestion.source.database.bigquery import BigquerySource

"""
Check Partitioned Table in Profiler Workflow
"""

mock_bigquery_config = {
    "source": {
        "type": "bigquery",
        "serviceName": "local_bigquery7",
        "serviceConnection": {
            "config": {"type": "BigQuery", "credentials": {"gcsConfig": {}}}
        },
        "sourceConfig": {
            "config": {
                "type": "DatabaseMetadata",
            }
        },
    },
    "sink": {"type": "metadata-rest", "config": {}},
    "workflowConfig": {
        "openMetadataServerConfig": {
            "hostPort": "http://localhost:8585/api",
            "authProvider": "no-auth",
        }
    },
}

TEST_PARTITION = {"schema_name": "test_schema", "table_name": "test_table"}

MOCK_DATABASE = Database(
    id="2aaa012e-099a-11ed-861d-0242ac120002",
    name="118146679784",
    fullyQualifiedName="bigquery_source.bigquery.db",
    displayName="118146679784",
    description="",
    service=EntityReference(
        id="85811038-099a-11ed-861d-0242ac120002",
        type="databaseService",
    ),
)


class MockTable(BaseModel):
    time_partitioning: Optional[TimePartitioning]
    range_partitioning: Optional[RangePartitioning]

    class Config:
        arbitrary_types_allowed = True


MOCK_TIME_UNIT_PARTITIONING = TimePartitioning(
    expiration_ms=None, field="test_column", type_="DAY"
)

MOCK_INGESTION_TIME_PARTITIONING = TimePartitioning(expiration_ms=None, type_="HOUR")

MOCK_RANGE_PARTITIONING = RangePartitioning(
    field="test_column", range_=PartitionRange(end=100, interval=10, start=0)
)


class BigqueryUnitTest(TestCase):
    @patch("metadata.ingestion.source.database.common_db_source.test_connection")
    def __init__(self, methodName, test_connection) -> None:
        super().__init__(methodName)
        test_connection.return_value = False
        self.config = OpenMetadataWorkflowConfig.parse_obj(mock_bigquery_config)
        self.bigquery_source = BigquerySource.create(
            mock_bigquery_config["source"],
            self.config.workflowConfig.openMetadataServerConfig,
        )
        self.bigquery_source.context.__dict__["database"] = MOCK_DATABASE
        self.bigquery_source.client = Client()
        self.inspector = types.SimpleNamespace()

        unittest.mock.patch.object(Table, "object")

    def test_time_unit_partition(self):
        self.bigquery_source.client.get_table = lambda fqn: MockTable(
            time_partitioning=MOCK_TIME_UNIT_PARTITIONING
        )
        bool_resp, partition = self.bigquery_source.get_table_partition_details(
            schema_name=TEST_PARTITION.get("schema_name"),
            table_name=TEST_PARTITION.get("table_name"),
            inspector=self.inspector,
        )

        assert partition.columns == ["test_column"]
        assert partition.intervalType.value == IntervalType.TIME_UNIT.value
        assert partition.interval == "DAY"
        assert bool_resp

    def test_ingestion_time_partition(self):
        self.bigquery_source.client.get_table = lambda fqn: MockTable(
            time_partitioning=MOCK_INGESTION_TIME_PARTITIONING
        )
        bool_resp, partition = self.bigquery_source.get_table_partition_details(
            schema_name=TEST_PARTITION.get("schema_name"),
            table_name=TEST_PARTITION.get("table_name"),
            inspector=self.inspector,
        )

        assert partition.intervalType.value == IntervalType.INGESTION_TIME.value
        assert partition.interval == "HOUR"
        assert bool_resp

    def test_range_partition(self):
        self.bigquery_source.client.get_table = lambda fqn: MockTable(
            time_partitioning=None, range_partitioning=MOCK_RANGE_PARTITIONING
        )

        bool_resp, partition = self.bigquery_source.get_table_partition_details(
            schema_name=TEST_PARTITION.get("schema_name"),
            table_name=TEST_PARTITION.get("table_name"),
            inspector=self.inspector,
        )

        assert partition.intervalType.value == IntervalType.INTEGER_RANGE.value
        assert partition.interval == 10
        assert bool_resp

    def test_no_partition(self):
        self.bigquery_source.client.get_table = lambda fqn: MockTable(
            time_partitioning=None, range_partitioning=None
        )

        bool_resp, partition = self.bigquery_source.get_table_partition_details(
            schema_name=TEST_PARTITION.get("schema_name"),
            table_name=TEST_PARTITION.get("table_name"),
            inspector=self.inspector,
        )

        assert not bool_resp
        assert not partition
