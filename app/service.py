# Copyright 2016, 2017 John J. Rofrano. All Rights Reserved.
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

"""
Products Service
Paths:
------
GET /products - Returns a list all of the Products
GET /product/{id} - Returns the Product with a given id number
POST /products - creates a new Product record in the database
PUT /products/{id} - updates a Product record in the database
DELETE /products/{id} - deletes a Product record in the database
"""

import os
import sys
import logging
from flask import Flask, jsonify, request, url_for, make_response, abort
from flask_api import status    # HTTP Status Codes
from werkzeug.exceptions import NotFound

# For this example we'll use SQLAlchemy, a popular ORM that supports a
# variety of backends including SQLite, MySQL, and PostgreSQL
from flask_sqlalchemy import SQLAlchemy
from models import Products, DataValidationError

# Import Flask application
from app import app

######################################################################
# Error Handlers
######################################################################
@app.errorhandler(DataValidationError)
def request_validation_error(error):
    """ Handles Value Errors from bad data """
    return bad_request(error)

@app.errorhandler(status.HTTP_400_BAD_REQUEST)
def bad_request(error):
    """ Handles bad reuests with 400_BAD_REQUEST """
    message = error.message or str(error)
    app.logger.warning(message)
    return jsonify(status=status.HTTP_400_BAD_REQUEST,
                   error='Bad Request',
                   message=message), status.HTTP_400_BAD_REQUEST

@app.errorhandler(status.HTTP_404_NOT_FOUND)
def not_found(error):
    """ Handles resources not found with 404_NOT_FOUND """
    message = error.message or str(error)
    app.logger.warning(message)
    return jsonify(status=status.HTTP_404_NOT_FOUND,
                   error='Not Found',
                   message=message), status.HTTP_404_NOT_FOUND

@app.errorhandler(status.HTTP_405_METHOD_NOT_ALLOWED)
def method_not_supported(error):
    """ Handles unsuppoted HTTP methods with 405_METHOD_NOT_SUPPORTED """
    message = error.message or str(error)
    app.logger.warning(message)
    return jsonify(status=status.HTTP_405_METHOD_NOT_ALLOWED,
                   error='Method not Allowed',
                   message=message), status.HTTP_405_METHOD_NOT_ALLOWED

@app.errorhandler(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
def mediatype_not_supported(error):
    """ Handles unsuppoted media requests with 415_UNSUPPORTED_MEDIA_TYPE """
    message = error.message or str(error)
    app.logger.warning(message)
    return jsonify(status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                   error='Unsupported media type',
                   message=message), status.HTTP_415_UNSUPPORTED_MEDIA_TYPE

@app.errorhandler(status.HTTP_500_INTERNAL_SERVER_ERROR)
def internal_server_error(error):
    """ Handles unexpected server error with 500_SERVER_ERROR """
    message = error.message or str(error)
    app.logger.error(message)
    return jsonify(status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                   error='Internal Server Error',
                   message=message), status.HTTP_500_INTERNAL_SERVER_ERROR


######################################################################
# GET INDEX
######################################################################
@app.route('/', methods=['GET'])
def index():
    """ Root URL response """
    return app.send_static_file('index.html')

# @app.route('/')
# def index():
#     """ Root URL response """
#     return jsonify(name='Product Demo REST API Service',
#                    version='1.0',
#                    paths=url_for('list_products', _external=True)
#                   ), status.HTTP_200_OK

######################################################################
# LIST ALL Products
######################################################################
@app.route('/products', methods=['GET'])

def list_products():
    """ Returns all of the Products """

    app.logger.info('Request for product list')
    products = []
    category = request.args.get('category')
    name = request.args.get('name')
    price = request.args.get('price')
    if category:
        products = Products.find_by_category(category)
    elif name:
        products = Products.find_by_name(name)
    elif price:
        products = Products.find_by_price(price)
    else:
        products = Products.all()

    results = [product.serialize() for product in products]
    return make_response(jsonify(results), status.HTTP_200_OK)


######################################################################
# RETRIEVE A Product
######################################################################
@app.route('/products/<int:product_id>', methods=['GET'])
def get_products(product_id):
    """
    Retrieve a single Product

    This endpoint will return a Product based on it's id
    """
    app.logger.info('Request for product with id: %s', product_id)
    product = Products.find(product_id)
    if not product:
        raise NotFound("Product with id '{}' was not found.".format(product_id))
    return make_response(jsonify(product.serialize()), status.HTTP_200_OK)


######################################################################
# ADD A NEW Product
######################################################################
@app.route('/products', methods=['POST'])
def create_products():
    """
    Creates a Product
    This endpoint will create a Product based on the data in the body that is posted
    """
    app.logger.info('Request to create a product')
    check_content_type('application/json')
    product = Products()
    product.deserialize(request.get_json())
    product.save()
    message = product.serialize()
    location_url = url_for('get_products', product_id=product.id, _external=True)
    return make_response(jsonify(message), status.HTTP_201_CREATED,
                         {
                             'Location': location_url
                         })


######################################################################
# UPDATE AN EXISTING Product
######################################################################
@app.route('/products/<int:product_id>', methods=['PUT'])
def update_products(product_id):
    """
    Update a Product

    This endpoint will update a Product based the body that is posted
    """
    app.logger.info('Request to update product with id: %s', product_id)
    check_content_type('application/json')
    product = Products.find(product_id)
    if not product:
        raise NotFound("Product with id '{}' was not found.".format(product_id))
    product.deserialize(request.get_json())
    product.id = product_id
    product.save()
    return make_response(jsonify(product.serialize()), status.HTTP_200_OK)

@app.route('/products/<int:product_id>/unavailable', methods=['PUT'])
def unavailable_products(product_id):
    """
    Make a product unavailable

    This endpoint will update a Product to be unavailable
    """
    app.logger.info('Request to update product with id: %s', product_id)
    product = Products.find(product_id)
    if not product:
        raise NotFound("Product with id '{}' was not found.".format(product_id))
    product.id = product_id
    product.available = False
    product.save()
    return make_response(jsonify(product.serialize()), status.HTTP_200_OK)

######################################################################
# DELETE A PRODUCT
######################################################################

@app.route('/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    """
    Delete a Product

    This endpoint will delete a Product based the id specified in the path
    """
    app.logger.info('Request to delete product with id: %s', product_id)
    product = Products.find(product_id)
    if product:
        product.delete()
    return make_response('', status.HTTP_204_NO_CONTENT)

######################################################################
#  Delete ALL DATA!!! For Testing Only
######################################################################
@app.route('/products/reset', methods=['DELETE'])
def reset_all():
    ''' Removes all products from the DB '''
    Products.delete_all()
    return make_response('', status.HTTP_204_NO_CONTENT)

######################################################################
#  U T I L I T Y   F U N C T I O N S
######################################################################


def init_db():
    """ Initialies the SQLAlchemy app """
    global app
    Products.init_db(app)


def check_content_type(content_type):
    """ Checks that the media type is correct """
    if request.headers['Content-Type'] == content_type:
        return
    app.logger.error('Invalid Content-Type: %s', request.headers['Content-Type'])
    abort(415, 'Content-Type must be {}'.format(content_type))


def initialize_logging(log_level=logging.INFO):
    """ Initialized the default logging to STDOUT """
    if not app.debug:
        print('Setting up logging...')
        # Set up default logging for submodules to use STDOUT
        # datefmt='%m/%d/%Y %I:%M:%S %p'
        fmt = '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
        logging.basicConfig(stream=sys.stdout, level=log_level, format=fmt)
        # Make a new log handler that uses STDOUT
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(fmt))
        handler.setLevel(log_level)
        # Remove the Flask default handlers and use our own
        handler_list = list(app.logger.handlers)
        for log_handler in handler_list:
            app.logger.removeHandler(log_handler)
        app.logger.addHandler(handler)
        app.logger.setLevel(log_level)
        app.logger.info('Logging handler established')


######################################################################
# GET HEALTH CHECK
######################################################################
@app.route('/healthcheck')
def healthcheck():
    """ Let them know our heart is still beating """
    return make_response(jsonify(status=200, message='Healthy'), status.HTTP_200_OK)