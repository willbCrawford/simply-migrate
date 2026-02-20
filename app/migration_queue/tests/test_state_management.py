import unittest
from unittest.mock import Mock, patch
from datetime import datetime
import json

from app.migration_queue import StateManager, MigrationStatus, TenantMigrationResult, MigrationJobState
from app.models import StartMigrationTenantRequest


class TestStateManager(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures before each test"""
        self.mock_redis = Mock()
        self.state_manager = StateManager(self.mock_redis)
        self.test_job_id = "test-job-123"
        self.test_tenants = [
            StartMigrationTenantRequest(
                tenant_id = "1",
                tenant_name="tenant1",
                user="tenant_user",
                password="password",
                database_name="tenant",
                host="localhost",
                connection_string=""
            ),
            StartMigrationTenantRequest(
                tenant_id = "1",
                tenant_name="tenant2",
                user="tenant_user",
                password="password",
                database_name="tenant",
                host="localhost",
                connection_string=""
            ),
            StartMigrationTenantRequest(
                tenant_id = "1",
                tenant_name="tenant3",
                user="tenant_user",
                password="password",
                database_name="tenant",
                host="localhost",
                connection_string=""
            )
        ]

    def tearDown(self):
        """Clean up after each test"""
        self.mock_redis.reset_mock()

    def test_create_job(self):
        """Test creating a new migration job"""
        result = self.state_manager.create_job(self.test_job_id, self.test_tenants)

        self.assertEqual(result.job_id, self.test_job_id)
        self.assertEqual(result.status, MigrationStatus.PENDING)
        self.assertEqual(result.tenants, ["tenant1", "tenant2", "tenant3"])
        self.assertEqual(result.total_tenants, 3)
        self.assertEqual(result.completed_tenants, 0)
        self.assertEqual(result.successful_tenants, 0)
        self.assertEqual(result.failed_tenants, 0)
        self.assertEqual(result.tenant_results, {})
        self.assertIsNone(result.completed_at)

        self.mock_redis.setex.assert_called_once()

    def test_get_job_success(self):
        """Test retrieving an existing job"""
        mock_job_data = {
            "job_id": self.test_job_id,
            "status": "pending",
            "tenants": ["tenant1"],
            "total_tenants": 1,
            "completed_tenants": 0,
            "successful_tenants": 0,
            "failed_tenants": 0,
            "tenant_results": {},
            "started_at": "2024-01-15T10:30:00",
            "completed_at": None
        }
        self.mock_redis.get.return_value = json.dumps(mock_job_data)

        result = self.state_manager.get_job(self.test_job_id)

        self.assertIsNotNone(result)
        self.assertEqual(result.job_id, self.test_job_id)
        self.assertEqual(result.status, MigrationStatus.PENDING)
        self.mock_redis.get.assert_called_once_with(f"migration:job:{self.test_job_id}")

    def test_get_job_not_found(self):
        """Test retrieving a non-existent job"""
        self.mock_redis.get.return_value = None

        result = self.state_manager.get_job("non-existent-job")

        self.assertIsNone(result)

    def test_get_job_with_tenant_results(self):
        """Test retrieving a job with tenant results"""
        mock_job_data = {
            "job_id": self.test_job_id,
            "status": "running",
            "tenants": ["tenant1"],
            "total_tenants": 1,
            "completed_tenants": 1,
            "successful_tenants": 1,
            "failed_tenants": 0,
            "tenant_results": {
                "tenant1": {
                    "tenant_id": "tenant1",
                    "status": "success",
                    "scripts_applied": [],
                    "scripts_skipped": [],
                    "callback_metadata": {}
                }
            },
            "started_at": "2024-01-15T10:30:00",
            "completed_at": None
        }
        self.mock_redis.get.return_value = json.dumps(mock_job_data)

        result = self.state_manager.get_job(self.test_job_id)

        self.assertIsNotNone(result)
        self.assertIn("tenant1", result.tenant_results)
        self.assertIsInstance(result.tenant_results["tenant1"], TenantMigrationResult)
        self.assertEqual(result.tenant_results["tenant1"].tenant_id, "tenant1")

    @patch('datetime.datetime')
    def test_update_job_status_to_running(self, mock_datetime):
        """Test updating job status to running"""
        mock_job_data = {
            "job_id": self.test_job_id,
            "status": "pending",
            "tenants": ["tenant1"],
            "total_tenants": 1,
            "completed_tenants": 0,
            "successful_tenants": 0,
            "failed_tenants": 0,
            "tenant_results": {},
            "started_at": "2024-01-15T10:30:00",
            "completed_at": None
        }
        self.mock_redis.get.return_value = json.dumps(mock_job_data)

        self.state_manager.update_job_status(self.test_job_id, MigrationStatus.RUNNING)

        self.mock_redis.setex.assert_called_once()

    @patch('datetime.datetime')
    def test_update_job_status_to_success_sets_completed_at(self, mock_datetime):
        """Test that updating to SUCCESS status sets completed_at"""
        mock_now = datetime(2024, 1, 15, 11, 0, 0)
        mock_datetime.utcnow.return_value = mock_now

        mock_job_data = {
            "job_id": self.test_job_id,
            "status": "running",
            "tenants": ["tenant1"],
            "total_tenants": 1,
            "completed_tenants": 1,
            "successful_tenants": 1,
            "failed_tenants": 0,
            "tenant_results": {},
            "started_at": "2024-01-15T10:30:00",
            "completed_at": None
        }
        self.mock_redis.get.return_value = json.dumps(mock_job_data)

        self.state_manager.update_job_status(self.test_job_id, MigrationStatus.SUCCESS)

        call_args = self.mock_redis.setex.call_args
        saved_data = json.loads(call_args[0][2])
        self.assertIsNotNone(saved_data['completed_at'])

    def test_update_job_status_nonexistent_job(self):
        """Test updating status of a non-existent job"""
        self.mock_redis.get.return_value = None

        self.state_manager.update_job_status("non-existent", MigrationStatus.SUCCESS)

        self.mock_redis.setex.assert_not_called()

    @patch('datetime.datetime')
    def test_update_tenant_result_success(self, mock_datetime):
        """Test updating tenant result with successful migration"""
        mock_job_data = {
            "job_id": self.test_job_id,
            "status": "running",
            "tenants": ["tenant1"],
            "total_tenants": 1,
            "completed_tenants": 0,
            "successful_tenants": 0,
            "failed_tenants": 0,
            "tenant_results": {},
            "started_at": "2024-01-15T10:30:00",
            "completed_at": None
        }
        self.mock_redis.get.return_value = json.dumps(mock_job_data)

        tenant_result = TenantMigrationResult(
            tenant_id="tenant1",
            status=MigrationStatus.SUCCESS
        )

        self.state_manager.update_tenant_result(self.test_job_id, tenant_result)

        call_args = self.mock_redis.setex.call_args
        saved_data = json.loads(call_args[0][2])
        self.assertEqual(saved_data['completed_tenants'], 1)
        self.assertEqual(saved_data['successful_tenants'], 1)
        self.assertEqual(saved_data['failed_tenants'], 0)

    @patch('datetime.datetime')
    def test_update_tenant_result_failure(self, mock_datetime):
        """Test updating tenant result with failed migration"""
        mock_job_data = {
            "job_id": self.test_job_id,
            "status": "running",
            "tenants": ["tenant1"],
            "total_tenants": 1,
            "completed_tenants": 0,
            "successful_tenants": 0,
            "failed_tenants": 0,
            "tenant_results": {},
            "started_at": "2024-01-15T10:30:00",
            "completed_at": None
        }
        self.mock_redis.get.return_value = json.dumps(mock_job_data)

        tenant_result = TenantMigrationResult(
            tenant_id="tenant1",
            status=MigrationStatus.FAILED
        )

        self.state_manager.update_tenant_result(self.test_job_id, tenant_result)

        call_args = self.mock_redis.setex.call_args
        saved_data = json.loads(call_args[0][2])
        self.assertEqual(saved_data['completed_tenants'], 1)
        self.assertEqual(saved_data['successful_tenants'], 0)
        self.assertEqual(saved_data['failed_tenants'], 1)

    @patch('datetime.datetime')
    def test_update_tenant_result_completes_job_all_success(self, mock_datetime):
        """Test that job status updates to SUCCESS when all tenants succeed"""
        mock_now = datetime(2024, 1, 15, 11, 0, 0)
        mock_datetime.utcnow.return_value = mock_now

        mock_job_data = {
            "job_id": self.test_job_id,
            "status": "running",
            "tenants": ["tenant1", "tenant2"],
            "total_tenants": 2,
            "completed_tenants": 1,
            "successful_tenants": 1,
            "failed_tenants": 0,
            "tenant_results": {},
            "started_at": "2024-01-15T10:30:00",
            "completed_at": None
        }
        self.mock_redis.get.return_value = json.dumps(mock_job_data)

        tenant_result = TenantMigrationResult(
            tenant_id="tenant2",
            status=MigrationStatus.SUCCESS
        )

        self.state_manager.update_tenant_result(self.test_job_id, tenant_result)

        call_args = self.mock_redis.setex.call_args
        saved_data = json.loads(call_args[0][2])
        self.assertEqual(saved_data['status'], MigrationStatus.SUCCESS.value)
        self.assertEqual(saved_data['completed_at'], mock_now.isoformat())

    @patch('datetime.datetime')
    def test_update_tenant_result_completes_job_all_failed(self, mock_datetime):
        """Test that job status updates to FAILED when all tenants fail"""
        mock_now = datetime(2024, 1, 15, 11, 0, 0)
        mock_datetime.utcnow.return_value = mock_now

        mock_job_data = {
            "job_id": self.test_job_id,
            "status": "running",
            "tenants": ["tenant1", "tenant2"],
            "total_tenants": 2,
            "completed_tenants": 1,
            "successful_tenants": 0,
            "failed_tenants": 1,
            "tenant_results": {},
            "started_at": "2024-01-15T10:30:00",
            "completed_at": None
        }
        self.mock_redis.get.return_value = json.dumps(mock_job_data)

        tenant_result = TenantMigrationResult(
            tenant_id="tenant2",
            status=MigrationStatus.FAILED
        )

        self.state_manager.update_tenant_result(self.test_job_id, tenant_result)

        call_args = self.mock_redis.setex.call_args
        saved_data = json.loads(call_args[0][2])
        self.assertEqual(saved_data['status'], MigrationStatus.FAILED.value)
        self.assertEqual(saved_data['completed_at'], mock_now.isoformat())

    @patch('datetime.datetime')
    def test_update_tenant_result_completes_job_partial_success(self, mock_datetime):
        """Test that job status updates to PARTIAL when some tenants succeed and some fail"""
        mock_now = datetime(2024, 1, 15, 11, 0, 0)
        mock_datetime.utcnow.return_value = mock_now

        mock_job_data = {
            "job_id": self.test_job_id,
            "status": "running",
            "tenants": ["tenant1", "tenant2"],
            "total_tenants": 2,
            "completed_tenants": 1,
            "successful_tenants": 1,
            "failed_tenants": 0,
            "tenant_results": {},
            "started_at": "2024-01-15T10:30:00",
            "completed_at": None
        }
        self.mock_redis.get.return_value = json.dumps(mock_job_data)

        tenant_result = TenantMigrationResult(
            tenant_id="tenant2",
            status=MigrationStatus.FAILED
        )

        self.state_manager.update_tenant_result(self.test_job_id, tenant_result)

        call_args = self.mock_redis.setex.call_args
        saved_data = json.loads(call_args[0][2])
        self.assertEqual(saved_data['status'], MigrationStatus.PARTIAL.value)
        self.assertEqual(saved_data['completed_at'], mock_now.isoformat())

    def test_update_tenant_result_nonexistent_job(self):
        """Test updating tenant result for non-existent job"""
        self.mock_redis.get.return_value = None

        tenant_result = TenantMigrationResult(
            tenant_id="tenant1",
            status=MigrationStatus.SUCCESS
        )

        self.state_manager.update_tenant_result("non-existent", tenant_result)

        self.mock_redis.setex.assert_not_called()

    def test_serialize_for_celery_enum(self):
        """Test serializing Enum values"""
        result = self.state_manager.serialize_for_celery(MigrationStatus.SUCCESS)
        self.assertEqual(result, "success")

    def test_serialize_for_celery_dataclass(self):
        """Test serializing dataclass objects"""
        tenant_result = TenantMigrationResult(
            tenant_id="tenant1",
            status=MigrationStatus.SUCCESS
        )

        result = self.state_manager.serialize_for_celery(tenant_result)

        self.assertIsInstance(result, dict)
        self.assertEqual(result['tenant_id'], "tenant1")
        self.assertEqual(result['status'], "success")
        self.assertEqual(result['message'], "Done")

    def test_serialize_for_celery_dict(self):
        """Test serializing dictionaries"""
        data = {
            "status": MigrationStatus.PENDING,
            "count": 5
        }

        result = self.state_manager.serialize_for_celery(data)

        self.assertEqual(result['status'], "pending")
        self.assertEqual(result['count'], 5)

    def test_serialize_for_celery_list(self):
        """Test serializing lists"""
        data = [MigrationStatus.SUCCESS, MigrationStatus.FAILED]

        result = self.state_manager.serialize_for_celery(data)

        self.assertEqual(result, ["success", "failed"])

    def test_serialize_for_celery_datetime(self):
        """Test serializing datetime objects"""
        dt = datetime(2024, 1, 15, 10, 30, 0)

        result = self.state_manager.serialize_for_celery(dt)

        self.assertEqual(result, "2024-01-15T10:30:00")

    def test_save_job(self):
        """Test saving job to Redis"""
        job = MigrationJobState(
            job_id=self.test_job_id,
            status=MigrationStatus.PENDING,
            tenants=["tenant1"],
            total_tenants=1,
            completed_tenants=0,
            successful_tenants=0,
            failed_tenants=0,
            tenant_results={},
            started_at="2024-01-15T10:30:00"
        )

        self.state_manager._save_job(job)

        self.mock_redis.setex.assert_called_once()
        call_args = self.mock_redis.setex.call_args
        self.assertEqual(call_args[0][0], f"migration:job:{self.test_job_id}")
        self.assertEqual(call_args[0][1], 86400 * 7)  # 7 days TTL

        saved_data = json.loads(call_args[0][2])
        self.assertEqual(saved_data['job_id'], self.test_job_id)
        self.assertEqual(saved_data['status'], "pending")

    def test_get_all_jobs(self):
        """Test retrieving all jobs"""
        job1_data = {
            "job_id": "job1",
            "status": "success",
            "tenants": ["tenant1"],
            "total_tenants": 1,
            "completed_tenants": 1,
            "successful_tenants": 1,
            "failed_tenants": 0,
            "tenant_results": {},
            "started_at": "2024-01-15T10:30:00"
        }
        job2_data = {
            "job_id": "job2",
            "status": "failed",
            "tenants": ["tenant2"],
            "total_tenants": 1,
            "completed_tenants": 1,
            "successful_tenants": 0,
            "failed_tenants": 1,
            "tenant_results": {},
            "started_at": "2024-01-15T09:00:00"
        }

        self.mock_redis.keys.return_value = [
            b"migration:job:job1",
            b"migration:job:job2"
        ]
        self.mock_redis.get.side_effect = [
            json.dumps(job1_data),
            json.dumps(job2_data)
        ]

        result = self.state_manager.get_all_jobs()

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].job_id, "job1")  # Sorted by started_at, descending
        self.assertEqual(result[1].job_id, "job2")

    def test_get_all_jobs_with_limit(self):
        """Test retrieving jobs with limit"""
        self.mock_redis.keys.return_value = [f"migration:job:job{i}" for i in range(100)]
        self.mock_redis.get.return_value = json.dumps({
            "job_id": "job1",
            "status": "success",
            "tenants": [],
            "total_tenants": 0,
            "completed_tenants": 0,
            "successful_tenants": 0,
            "failed_tenants": 0,
            "tenant_results": {},
            "started_at": "2024-01-15T10:30:00"
        })

        result = self.state_manager.get_all_jobs(limit=10)

        self.assertLessEqual(len(result), 10)

    def test_get_all_jobs_empty(self):
        """Test retrieving jobs when none exist"""
        self.mock_redis.keys.return_value = []

        result = self.state_manager.get_all_jobs()

        self.assertEqual(result, [])

    def test_get_job_dict(self):
        """Test get_job_dict parsing"""
        data = json.dumps({
            "job_id": self.test_job_id,
            "status": "running",
            "tenant_results": {
                "tenant1": {
                    "tenant_id": "tenant1",
                    "status": "success",
                    "scripts_applied": [],
                    "scripts_skipped": [],
                    "callback_metadata": {}
                }
            }
        })

        result = self.state_manager.get_job_dict(data)

        self.assertIn("tenant_results", result)
        self.assertIsInstance(result["tenant_results"]["tenant1"], TenantMigrationResult)
        self.assertEqual(result["tenant_results"]["tenant1"].tenant_id, "tenant1")
