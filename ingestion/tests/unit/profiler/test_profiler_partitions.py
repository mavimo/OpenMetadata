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

from typing import Optional
from unittest import TestCase
from unittest.mock import patch

from google.cloud.bigquery import PartitionRange, RangePartitioning, TimePartitioning
from pydantic import BaseModel

from metadata.generated.schema.entity.data.database import Database
from metadata.generated.schema.entity.data.table import IntervalType, TablePartition
from metadata.generated.schema.type.entityReference import EntityReference
from metadata.orm_profiler.api.workflow import ProfilerWorkflow

"""
Check Partitioned Table in Profiler Workflow
"""

mock_bigquery_config = {
    "source": {
        "type": "bigquery",
        "serviceName": "local_bigquery",
        "serviceConnection": {
            "config": {"type": "BigQuery", "credentials": {"gcsConfig": {}}}
        },
        "sourceConfig": {
            "config": {
                "type": "Profiler",
            }
        },
    },
    "processor": {
        "type": "orm-profiler",
        "config": {
            "profiler": {
                "name": "my_profiler",
                "timeout_seconds": 60,
                "metrics": ["row_count", "min", "max", "COUNT", "null_count"],
            },
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
    tablePartition: Optional[TablePartition]

    class Config:
        arbitrary_types_allowed = True


MOCK_TIME_UNIT_PARTITIONING = TimePartitioning(
    expiration_ms=None, field="test_column", type_="DAY"
)

MOCK_INGESTION_TIME_PARTITIONING = TimePartitioning(expiration_ms=None, type_="HOUR")

MOCK_RANGE_PARTITIONING = RangePartitioning(
    field="test_column", range_=PartitionRange(end=100, interval=10, start=0)
)


class ProfilerPartitionUnitTest(TestCase):
    @patch("metadata.orm_profiler.api.workflow.ProfilerWorkflow._validate_service_name")
    def __init__(self, methodName, validate_service_name):
        super().__init__(methodName)
        validate_service_name.return_value = True
        self.profiler_workflow = ProfilerWorkflow.create(mock_bigquery_config)

    def test_partition_details_time_unit(self):
        table_entity = MockTable(
            tablePartition=TablePartition(
                columns=["e"], intervalType=IntervalType.TIME_UNIT, interval="DAY"
            )
        )
        resp = self.profiler_workflow.get_partition_details(table_entity)

        assert resp.partitionField == "e"
        assert resp.partitionQueryDuration == 30
        assert not resp.partitionValues

    def test_partition_details_ingestion_time_date(self):
        table_entity = MockTable(
            tablePartition=TablePartition(
                columns=["e"], intervalType=IntervalType.INGESTION_TIME, interval="DAY"
            )
        )
        resp = self.profiler_workflow.get_partition_details(table_entity)

        assert resp.partitionField == "_PARTITIONDATE"
        assert resp.partitionQueryDuration == 30
        assert not resp.partitionValues

    def test_partition_details_ingestion_time_hour(self):
        table_entity = MockTable(
            tablePartition=TablePartition(
                columns=["e"], intervalType=IntervalType.INGESTION_TIME, interval="HOUR"
            )
        )
        resp = self.profiler_workflow.get_partition_details(table_entity)

        assert resp.partitionField == "_PARTITIONTIME"
        assert resp.partitionQueryDuration == 30
        assert not resp.partitionValues
