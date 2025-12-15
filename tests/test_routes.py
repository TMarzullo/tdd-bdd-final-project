######################################################################
# Copyright 2016, 2023 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
######################################################################
"""
Product API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
  codecov --token=$CODECOV_TOKEN

  While debugging just these tests it's convenient to use this:
    nosetests --stop tests/test_service.py:TestProductService
"""
import os
import logging
from decimal import Decimal
from unittest import TestCase
from service import app
from service.common import status
from service.models import db, init_db, Product, Category
from tests.factories import ProductFactory

# Disable all but critical errors during normal test run
# uncomment for debugging failing tests
# logging.disable(logging.CRITICAL)

# DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///../db/test.db')
DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)
BASE_URL = "/products"


######################################################################
#  T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestProductRoutes(TestCase):
    """Product Service tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        # Set up the test database
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Run once after all tests"""
        db.session.close()

    def setUp(self):
        """Runs before each test"""
        self.client = app.test_client()
        db.session.query(Product).delete()  # clean up the last tests
        db.session.commit()

    def tearDown(self):
        db.session.remove()

    ############################################################
    # Utility function to bulk create products
    ############################################################
    def _create_products(self, count: int = 1) -> list:
        """Factory method to create products in bulk"""
        products = []
        for _ in range(count):
            test_product = ProductFactory()
            response = self.client.post(BASE_URL, json=test_product.serialize())
            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, "Could not create test product"
            )
            new_product = response.get_json()
            test_product.id = new_product["id"]
            products.append(test_product)
        return products

    ############################################################
    #  T E S T   C A S E S
    ############################################################
    def test_index(self):
        """It should return the index page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(b"Product Catalog Administration", response.data)

    def test_health(self):
        """It should be healthy"""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data['message'], 'OK')

    # ----------------------------------------------------------
    # TEST CREATE
    # ----------------------------------------------------------
    def test_create_product(self):
        """It should Create a new Product"""
        test_product = ProductFactory()
        logging.debug("Test Product: %s", test_product.serialize())
        response = self.client.post(BASE_URL, json=test_product.serialize())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_product = response.get_json()
        self.assertEqual(new_product["name"], test_product.name)
        self.assertEqual(new_product["description"], test_product.description)
        self.assertEqual(Decimal(new_product["price"]), test_product.price)
        self.assertEqual(new_product["available"], test_product.available)
        self.assertEqual(new_product["category"], test_product.category.name)

        #
        # Uncomment this code once READ is implemented
        #

        # # Check that the location header was correct
        # response = self.client.get(location)
        # self.assertEqual(response.status_code, status.HTTP_200_OK)
        # new_product = response.get_json()
        # self.assertEqual(new_product["name"], test_product.name)
        # self.assertEqual(new_product["description"], test_product.description)
        # self.assertEqual(Decimal(new_product["price"]), test_product.price)
        # self.assertEqual(new_product["available"], test_product.available)
        # self.assertEqual(new_product["category"], test_product.category.name)

    def test_create_product_with_no_name(self):
        """It should not Create a Product without a name"""
        product = self._create_products()[0]
        new_product = product.serialize()
        del new_product["name"]
        logging.debug("Product no name: %s", new_product)
        response = self.client.post(BASE_URL, json=new_product)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_product_no_content_type(self):
        """It should not Create a Product with no Content-Type"""
        response = self.client.post(BASE_URL, data="bad data")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_create_product_wrong_content_type(self):
        """It should not Create a Product with wrong Content-Type"""
        response = self.client.post(BASE_URL, data={}, content_type="plain/text")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_get_product(self):
        """It should Get a single Product"""
        # get the id of a product
        test_product = self._create_products(1)[0]
        response = self.client.get(f"{BASE_URL}/{test_product.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data["name"], test_product.name)

    def test_get_product_not_found(self):
        """It should not Get a Product thats not found"""
        response = self.client.get(f"{BASE_URL}/0")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        data = response.get_json()
        self.assertIn("was not found", data["message"])

    # ---------- UPDATE (success) ----------
    def test_update_product(self):
        """It should Update a Product"""
        # Create a product first
        product = self._create_products(1)[0]

        # Prepare an updated payload
        updated = product.serialize()
        updated["description"] = "Updated description"
        updated["price"] = "42.50"                 # payload uses string; model stores Decimal
        updated["available"] = not product.available
        updated["category"] = Category.TOOLS.name  # switch category

        # PUT /products/<id>
        response = self.client.put(f"{BASE_URL}/{product.id}", json=updated)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify response body
        data = response.get_json()
        self.assertEqual(data["description"], "Updated description")
        self.assertEqual(Decimal(data["price"]), Decimal("42.50"))
        self.assertEqual(data["available"], updated["available"])
        self.assertEqual(data["category"], Category.TOOLS.name)

        # GET back to confirm persisted change
        response = self.client.get(f"{BASE_URL}/{product.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data["description"], "Updated description")
        self.assertEqual(Decimal(data["price"]), Decimal("42.50"))
        self.assertEqual(data["available"], updated["available"])
        self.assertEqual(data["category"], Category.TOOLS.name)

    # ---------- UPDATE (fail) ----------

    def test_update_product_and_fail(self):
        """It should not Update a Product that does not exist"""
        template = ProductFactory()
        payload = template.serialize()
        payload["description"] = "Should not matter"

        # Not found
        response = self.client.put(f"{BASE_URL}/0", json=payload)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        data = response.get_json()
        self.assertIn("was not found", data["message"])

        # Wrong Content-Type (optional negative)
        response = self.client.put(f"{BASE_URL}/1", data=payload, content_type="text/plain")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    # ---------- DELETE (success) ----------

    def test_delete_product(self):
        """It should Delete a Product"""
        product = self._create_products(1)[0]

        # DELETE /products/<id>
        response = self.client.delete(f"{BASE_URL}/{product.id}")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Ensure it is gone
        response = self.client.get(f"{BASE_URL}/{product.id}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        data = response.get_json()
        self.assertIn("was not found", data["message"])

    # ---------- DELETE (fail) ----------

    def test_delete_product_and_fail(self):
        """It should not Delete a Product that does not exist"""
        response = self.client.delete(f"{BASE_URL}/0")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        data = response.get_json()
        self.assertIn("was not found", data["message"])

    # ---------- LIST ALL ----------

    def test_list_all_products(self):
        """It should List all Products"""
        start_count = self.get_product_count()

        # Create 3 products
        created = self._create_products(3)
        self.assertEqual(len(created), 3)

        # GET /products
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), start_count + 3)

        # Verify IDs present
        returned_ids = {p["id"] for p in data}
        expected_ids = {p.id for p in created}
        self.assertTrue(expected_ids.issubset(returned_ids))

    # ---------- LIST BY NAME ----------
    def test_list_by_name_product(self):
        """It should List Products by name"""
        products = self._create_products(4)

        # Choose name from the first product
        target_name = products[0].name

        # Update one other product to match this name
        updated = products[1].serialize()
        updated["name"] = target_name
        response = self.client.put(f"{BASE_URL}/{products[1].id}", json=updated)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # GET /products?name=<target_name>
        response = self.client.get(f"{BASE_URL}?name={target_name}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()

        # Count and verify names
        expected_count = sum(1 for p in products if p.name == target_name) + 1
        self.assertEqual(len(data), expected_count)
        for prod in data:
            self.assertEqual(prod["name"], target_name)

    # ---------- LIST BY CATEGORY ----------
    def test_list_by_category_product(self):
        """It should List Products by category"""
        products = self._create_products(5)

        # Force two products to a known category via update
        target_category = Category.FOOD.name
        for idx in (0, 2):
            payload = products[idx].serialize()
            payload["category"] = target_category
            response = self.client.put(f"{BASE_URL}/{products[idx].id}", json=payload)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        # GET /products?category=<target_category>
        response = self.client.get(f"{BASE_URL}?category={target_category}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()

        self.assertTrue(len(data) >= 2)
        for prod in data:
            self.assertEqual(prod["category"], target_category)

    def test_list_by_invalid_category_product(self):
        """It should Not List Products with an invalid category"""

        response = self.client.get(f"{BASE_URL}?category=InvalidCategory")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ---------- LIST BY AVAILABILITY ----------
    def test_list_by_availability_product(self):
        """It should List Products by availability"""
        products = self._create_products(6)

        # Flip availability on three products to True
        for idx in (1, 3, 5):
            payload = products[idx].serialize()
            payload["available"] = True
            response = self.client.put(f"{BASE_URL}/{products[idx].id}", json=payload)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        # GET /products?available=true
        response = self.client.get(f"{BASE_URL}?available=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    ######################################################################
    # Utility functions
    ######################################################################

    def get_product_count(self):
        """save the current number of products"""
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        # logging.debug("data = %s", data)
        return len(data)
