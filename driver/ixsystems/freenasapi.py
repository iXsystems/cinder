#  Copyright (c) 2016 iXsystems
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.
"""
FREENAS api for iXsystems FREENAS system.

Contains classes required to issue REST based api calls to FREENAS system.
"""

import base64

import ssl

import simplejson as json

import urllib.error
import urllib.parse
import urllib.request

from oslo_log import log as logging


LOG = logging.getLogger(__name__)


class FreeNASServer(object):
    """FreeNAS/TrueNAS server helper class, handle API level connection logic."""

    FREENAS_API_VERSION = "v2.0"
    TRANSPORT_TYPE = 'http'

    # FREENAS Commands
    SELECT_COMMAND = 'select'
    CREATE_COMMAND = 'create'
    UPDATE_COMMAND = 'update'
    DELETE_COMMAND = 'delete'

    # FREENAS API query tables
    REST_API_VOLUME = "/pool/dataset"
    REST_API_EXTENT = "/iscsi/extent"
    REST_API_TARGET = "/iscsi/target"
    REST_API_TARGET_TO_EXTENT = "/iscsi/targetextent"
    # REST_API_TARGET_GROUP = "/services/iscsi/targetgroup/"
    REST_API_SNAPSHOT = "/zfs/snapshot"
    ZVOLS = "zvols"
    TARGET_ID = -1  # We assume invalid id to begin with
    STORAGE_TABLE = "/storage"
    CLONE = "clone"
    # Command response format
    COMMAND_RESPONSE = {'status': '%s',
                        'response': '%s',
                        'code': -1}

    # Command status
    STATUS_OK = 'ok'
    STATUS_ERROR = 'error'

    def __init__(self, host, port,
                 username=None, password=None, apikey=None,
                 api_version=FREENAS_API_VERSION,
                 transport_type=TRANSPORT_TYPE):
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._apikey = apikey
        self.set_api_version(api_version)
        self.set_transport_type(transport_type)

    def get_host(self):
        """Get host name"""
        return self._host

    def get_port(self):
        """Get port number"""
        return self._port

    def get_username(self):
        """Get username"""
        return self._username

    def get_password(self):
        """Get password"""
        return self._password

    def get_transport_type(self):
        """Get API transport type http/https"""
        return self._protocol

    def set_host(self, host):
        """Set host"""        
        self._host = host

    def set_port(self, port):
        """Set port"""        
        try:
            int(port)
        except ValueError as value_error:
            raise ValueError("Port must be integer") from value_error

    def set_username(self, username):
        """Set username"""
        self._username = username

    def set_password(self, password):
        """Set password"""
        self._password = password

    def set_api_version(self, api_version):
        """Set API version"""
        self._api_version = api_version

    def set_transport_type(self, transport_type):
        """Set transport type"""
        self._protocol = transport_type

    def get_url(self):
        """Returns connection string.

           built using _protocol, _host, _port and _api_version fields
        """
        return f'{self._protocol}://{self._host}/api/{self._api_version}'

    def _create_request(self, request_d, param_list):
        """Creates urllib2.Request object."""
        headers = {'Content-Type': 'application/json'}

        if self._apikey != '':
            headers['Authorization'] = f'Bearer {self._apikey}'
        elif self._username != '' and self._password != '':
            loginstring = f'{self._username}:{self._password}'
            bloginstring = bytes(loginstring, encoding='utf8')
            bauth = base64.b64encode(bloginstring)
            auth = bauth.decode("utf8")
            headers['Authorization'] = f'Basic {auth}'
        else:
            raise ValueError("Username and password, or API key is required")

        url = self.get_url() + request_d
        LOG.debug('url : %s, request: %s', url, request_d)
        LOG.debug('param list : %s', param_list)
        return urllib.request.Request(url, param_list, headers)

    def _get_method(self, command_d):
        """Select http method based on FREENAS command."""
        if command_d == self.SELECT_COMMAND:
            return 'GET'
        if command_d == self.CREATE_COMMAND:
            return 'POST'
        if command_d == self.DELETE_COMMAND:
            return 'DELETE'
        if command_d == self.UPDATE_COMMAND:
            return 'PUT'
        else:
            return None

    def _parse_result(self, command_d, response_d):
        """parses the response upon execution of FREENAS API.

           COMMAND_RESPONSE is
           the dictionary object with status and response fields.
           If error, set status to ERROR else set it to OK
        """
        response_str = response_d.read()
        status = None
        if command_d == self.SELECT_COMMAND:
            status = self.STATUS_OK
            response_obj = response_str
        elif (command_d == self.CREATE_COMMAND or
              command_d == self.DELETE_COMMAND or
              command_d == self.UPDATE_COMMAND):
            response_obj = response_str
            status = self.STATUS_OK
        else:
            status = self.STATUS_ERROR
            response_obj = None

        self.COMMAND_RESPONSE['status'] = status
        self.COMMAND_RESPONSE['response'] = response_obj
        return self.COMMAND_RESPONSE

    def _get_error_info(self, err):
        """Collects error response message."""
        self.COMMAND_RESPONSE['status'] = self.STATUS_ERROR
        if isinstance(err, urllib.error.HTTPError):
            self.COMMAND_RESPONSE['response'] = f'{err.code}:{err.msg}'
            self.COMMAND_RESPONSE['code'] = err.code
        elif isinstance(err, urllib.error.URLError):
            self.COMMAND_RESPONSE['response'] = f'{str(err.reason.errno)}:\
                {err.reason.strerror}'
        else:
            return None
        return self.COMMAND_RESPONSE

    def invoke_command(self, command_d, request_d, param_list):
        """Invokes api and returns response object."""
        LOG.debug('invoke_command')
        request = self._create_request(request_d, param_list)
        method = self._get_method(command_d)
        if not method:
            raise FreeNASApiError("Invalid FREENAS command")
        request.get_method = lambda: method
        try:
            with urllib.request.urlopen(request,
                                    context=ssl.SSLContext()) as url_session:
                response_d = url_session.read()
            response = self._parse_result(command_d, response_d)
            LOG.debug("invoke_command : response for request %s : %s",
                      request_d, json.dumps(response))
        except urllib.error.HTTPError as http_exception:
            # LOG the error message received from FreeNAS/TrueNAS:
            # https://github.com/iXsystems/cinder/issues/11
            LOG.info('Error returned from server: "%s"',
                     json.loads(http_exception.read().decode('utf8'))['message'])
            error_d = self._get_error_info(http_exception)
            if error_d:
                return error_d
            raise FreeNASApiError(http_exception.code,
                                  http_exception.msg) from http_exception
        except Exception as exception_error:
            error_d = self._get_error_info(exception_error)
            if error_d:
                return error_d
            else:
                raise FreeNASApiError('Unexpected error',
                                      exception_error) from exception_error
        return response


class FreeNASApiError(Exception):
    """Base exception class for FREENAS api errors."""

    def __init__(self, code='unknown', message='unknown'):
        self.code = code
        self.message = message

    def __str__(self, *args, **kwargs):
        return f'FREENAS api failed. Reason - {self.code}:{self.message}'
