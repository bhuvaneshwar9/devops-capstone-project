"""
Account API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
"""
import os
import logging
from unittest import TestCase
from unittest.mock import patch
from tests.factories import AccountFactory
from service.common import status  # HTTP Status Codes
from service.models import db, Account, init_db
from service.routes import app

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)

BASE_URL = "/accounts"


######################################################################
#  T E S T   C A S E S
######################################################################
class TestAccountService(TestCase):
    """Account Service Tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Runs once before test suite"""

    def setUp(self):
        """Runs before each test"""
        db.session.query(Account).delete()  # clean up the last tests
        db.session.commit()

        self.client = app.test_client()

    def tearDown(self):
        """Runs once after each test case"""
        db.session.remove()

    ######################################################################
    #  H E L P E R   M E T H O D S
    ######################################################################

    def _create_accounts(self, count):
        """Factory method to create accounts in bulk"""
        accounts = []
        for _ in range(count):
            account = AccountFactory()
            response = self.client.post(BASE_URL, json=account.serialize())
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                "Could not create test Account",
            )
            new_account = response.get_json()
            account.id = new_account["id"]
            accounts.append(account)
        return accounts

    ######################################################################
    #  A C C O U N T   T E S T   C A S E S
    ######################################################################

    def test_index(self):
        """It should get 200_OK from the Home Page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_health(self):
        """It should be healthy"""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "OK")

    def test_create_account(self):
        """It should Create a new Account"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_account = response.get_json()
        self.assertEqual(new_account["name"], account.name)
        self.assertEqual(new_account["email"], account.email)
        self.assertEqual(new_account["address"], account.address)
        self.assertEqual(new_account["phone_number"], account.phone_number)
        self.assertEqual(new_account["date_joined"], str(account.date_joined))

    def test_bad_request(self):
        """It should not Create an Account when sending the wrong data"""
        response = self.client.post(BASE_URL, json={"name": "not enough data"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unsupported_media_type(self):
        """It should not Create an Account when sending the wrong media type"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="test/html"
        )
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_list_accounts(self):
        """It should Get a list of Accounts"""
        # Create a bunch of accounts
        self._create_accounts(5)
        
        # Get the list back
        resp = self.client.get(BASE_URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        
        # Check the data that was returned
        data = resp.get_json()
        self.assertEqual(len(data), 5)
    
    def test_list_empty_accounts(self):
        """It should return an empty list when no accounts exist"""
        resp = self.client.get(BASE_URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), 0)
        
    def test_method_not_allowed(self):
        """It should not allow a method that's not allowed"""
        resp = self.client.delete(BASE_URL)
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def test_bad_request_json(self):
        """It should return Bad Request for invalid JSON format"""
        resp = self.client.post(
            BASE_URL, 
            data="this is not valid json",
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        
    # Additional test to trigger HTTP_404_NOT_FOUND handler
    def test_get_account_not_found(self):
        """It should return 404 for an account that doesn't exist"""
        resp = self.client.get(f"{BASE_URL}/0")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
    
    # Test to trigger Method Not Allowed (405) error handler
    def test_method_not_allowed_put(self):
        """It should not allow PUT on the collection URL"""
        resp = self.client.put(BASE_URL)
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
    
    # Test to force an error that isn't explicitly handled 
    def test_internal_server_error(self):
        """It should trigger an internal server error"""
        # Mock Account.all to raise a generic exception
        with patch('service.models.Account.all') as mock_all:
            mock_all.side_effect = Exception("Internal Server Error")
            resp = self.client.get(BASE_URL)
            self.assertEqual(resp.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)