######################################################################
# Copyright 2016, 2022 John J. Rofrano. All Rights Reserved.
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

# spell: ignore Rofrano jsonify restx dbname
"""
Product Store Service with UI
"""
from flask import jsonify, request, abort
from flask import url_for  # noqa: F401 pylint: disable=unused-import
from service.models import Product, Category
from service.common import status  # HTTP Status Codes
from . import app


######################################################################
# H E A L T H   C H E C K
######################################################################
@app.route("/health")
def healthcheck():
    """Let them know our heart is still beating"""
    return jsonify(status=200, message="OK"), status.HTTP_200_OK


######################################################################
# H O M E   P A G E
######################################################################
@app.route("/")
def index():
    """Base URL for our service"""
    return app.send_static_file("index.html")


######################################################################
#  U T I L I T Y   F U N C T I O N S
######################################################################
def check_content_type(content_type):
    """Checks that the media type is correct"""
    if "Content-Type" not in request.headers:
        app.logger.error("No Content-Type specified.")
        abort(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Content-Type must be {content_type}",
        )

    if request.headers["Content-Type"] == content_type:
        return

    app.logger.error("Invalid Content-Type: %s", request.headers["Content-Type"])
    abort(
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        f"Content-Type must be {content_type}",
    )


######################################################################
# C R E A T E   A   N E W   P R O D U C T
######################################################################
@app.route("/products", methods=["POST"])
def create_products():
    """
    Creates a Product
    This endpoint will create a Product based the data in the body that is posted
    """
    app.logger.info("Request to Create a Product...")
    check_content_type("application/json")

    data = request.get_json()
    app.logger.info("Processing: %s", data)
    product = Product()
    product.deserialize(data)
    product.create()
    app.logger.info("Product with new id [%s] saved!", product.id)

    message = product.serialize()

    location_url = url_for("get_products", product_id=product.id, _external=True)
    return jsonify(message), status.HTTP_201_CREATED, {"Location": location_url}


######################################################################
# L I S T   A L L   P R O D U C T S
######################################################################
@app.route("/products", methods=["GET"])
def list_products():
    """
    Lists all Products, optionally filtered by:
	  - name
      - category: enum name (e.g., TOOLS, FOOD, CLOTHS, HOUSEWARES, AUTOMOTIVE)
      - available: boolean string (true/false, 1/0, yes/no)
    """
    app.logger.info("Request to List all Products...")

    name = request.args.get("name")
    category_name = request.args.get("category")   # e.g., "TOOLS"
    available_param = request.args.get("available")  # e.g., "true"

    # Start with the base query    # Start with the base query
    query = Product.query

    # --- Filter by name (exact match) ---
    if name:
        query = query.filter(Product.name == name)

    # --- Filter by category (enum) ---
    if category_name:
        try:
            category_enum = Category[category_name]  # raises KeyError if invalid
        except KeyError:
            abort(status.HTTP_400_BAD_REQUEST, f"Unknown category: {category_name}")
        query = query.filter(Product.category == category_enum)

    # --- Filter by availability (bool-like strings) ---
    if available_param is not None:
        val = available_param.strip().lower()
        if val in ("true", "1", "yes"):
            query = query.filter(Product.available.is_(True))
        elif val in ("false", "0", "no"):
            query = query.filter(Product.available.is_(False))
        else:
            abort(status.HTTP_400_BAD_REQUEST, f"Invalid available: {available_param}")

    products = query.all()
    results = [prod.serialize() for prod in products]

    return jsonify(results), status.HTTP_200_OK


######################################################################
# R E A D   A   P R O D U C T
######################################################################
@app.route("/products/<int:product_id>", methods=["GET"])
def get_products(product_id):
    """
    Reads a single Product by id
    """
    app.logger.info("Request to Read Product with id [%s]...", product_id)
    product = Product.find(product_id)
    if not product:
        abort(status.HTTP_404_NOT_FOUND, f"Product with id [{product_id}] was not found.")
    message = product.serialize()
    location_url = url_for("get_products", product_id=product.id, _external=True)
    return jsonify(message), status.HTTP_200_OK, {"Location": location_url}


######################################################################
# U P D A T E   A   P R O D U C T
######################################################################
@app.route("/products/<int:product_id>", methods=["PUT"])
def update_products(product_id):
    """
    Updates a Product by id
    """
    app.logger.info("Request to Update Product with id [%s]...", product_id)
    check_content_type("application/json")
    product = Product.find(product_id)
    if not product:
        abort(status.HTTP_404_NOT_FOUND, f"Product with id [{product_id}] was not found.")

    data = request.get_json()
    app.logger.info("Processing update payload: %s", data)

    # Apply incoming fields onto the existing product
    product.deserialize(data)
    product.update()
    return jsonify(product.serialize()), status.HTTP_200_OK


######################################################################
# D E L E T E   A   P R O D U C T
######################################################################
@app.route("/products/<int:product_id>", methods=["DELETE"])
def delete_products(product_id):
    """
    Deletes a Product by id
    """
    app.logger.info("Request to Delete Product with id [%s]...", product_id)
    product = Product.find(product_id)
    if not product:
        abort(status.HTTP_404_NOT_FOUND, f"Product with id [{product_id}] was not found.")

    product.delete()
    return jsonify({}), status.HTTP_204_NO_CONTENT
