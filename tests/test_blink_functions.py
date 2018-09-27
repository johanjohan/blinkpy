"""Tests camera and system functions."""
import time

import unittest
from unittest import mock

# import pytest

from blinkpy import blinkpy
from blinkpy.sync_module import BlinkSyncModule
from blinkpy.camera import BlinkCamera
from blinkpy.helpers.constants import BLINK_URL
import tests.mock_responses as mresp

USERNAME = 'foobar'
PASSWORD = 'deadbeef'


class MockSyncModule(BlinkSyncModule):
    """Mock http requests from sync module."""

    def __init__(self, blink, header):
        """Create mock sync module instance."""
        super().__init__(blink, header)
        self.blink = blink
        self.header = header
        self.return_value = None
        self.return_value2 = None

    def http_get(self, url, stream=False, json=True):
        """Mock get request."""
        if stream and self.return_value2 is not None:
            return self.return_value2
        return self.return_value

    def http_post(self, url):
        """Mock post request."""
        return self.return_value


class TestBlinkFunctions(unittest.TestCase):
    """Test Blink and BlinkCamera functions in blinkpy."""

    def setUp(self):
        """Set up Blink module."""
        self.blink = blinkpy.Blink(username=USERNAME,
                                   password=PASSWORD)
        # pylint: disable=protected-access
        self.blink._auth_header = {
            'Host': 'test.url.tld',
            'TOKEN_AUTH': 'foobar123'
        }
        self.blink.urls = blinkpy.BlinkURLHandler('test')
        self.config = {
            'device_id': 1111,
            'name': 'foobar',
            'armed': False,
            'active': 'disabled',
            'thumbnail': '/test',
            'video': '/test.mp4',
            'temp': 80,
            'battery': 3,
            'notifications': 2,
            'region_id': 'test',
            'device_type': 'camera'
        }
        self.blink.sync = MockSyncModule(
            self.blink, self.blink._auth_header)

        self.camera = BlinkCamera(self.config, self.blink.sync)

    def tearDown(self):
        """Clean up after test."""
        self.blink = None
        self.config = {}
        self.camera = None

    def test_image_refresh(self):
        """Test image refresh function."""
        self.blink.sync.return_value = {'devices': [self.config]}
        image = self.camera.image_refresh()
        self.assertEqual(image,
                         'https://rest.test.{}/test.jpg'.format(BLINK_URL))

    @mock.patch('blinkpy.sync_module.BlinkSyncModule.camera_config_request')
    @mock.patch('blinkpy.sync_module.BlinkSyncModule._video_request')
    def test_refresh(self, vid_req, req):
        """Test blinkpy refresh function."""
        req.return_value = {'foo': 'bar'}
        self.blink.sync.cameras = {'foobar': self.camera}
        self.blink.sync.return_value = {'devices': [{'foo': 'bar'}]}
        # pylint: disable=protected-access
        self.blink._last_summary = {'devices': [self.config]}
        # pylint: disable=protected-access
        self.blink._last_events = {'foo': 'bar'}
        vid_req.return_value = [
            {
                'camera_name': 'foobar',
                'address': '/new.mp4',
                'thumbnail': '/new',
            }
        ]
        self.blink.last_refresh = int(time.time())
        self.blink.refresh_rate = 100000
        self.blink.sync.refresh()
        test_camera = self.blink.sync.cameras['foobar']
        self.assertEqual(test_camera.clip,
                         'https://rest.test.{}/new.mp4'.format(BLINK_URL))
        self.assertEqual(test_camera.thumbnail,
                         'https://rest.test.{}/new.jpg'.format(BLINK_URL))

    def test_set_links(self):
        """Test the link set method."""
        self.blink.sync.cameras = {'foobar': self.camera}
        self.blink.network_id = 9999
        self.blink.sync.set_links()
        net_url = "{}/{}".format(self.blink.urls.network_url, 9999)
        self.assertEqual(self.camera.image_link,
                         "{}/camera/1111/thumbnail".format(net_url))
        self.assertEqual(self.camera.arm_link,
                         "{}/camera/1111/".format(net_url))

    @mock.patch('blinkpy.blinkpy.http_req')
    def test_backup_url(self, req):
        """Test backup login method."""
        req.side_effect = [
            mresp.mocked_requests_post(None),
            {'authtoken': {'authtoken': 'foobar123'}}
        ]
        self.blink.get_auth_token()
        self.assertEqual(self.blink.region_id, 'piri')
        self.assertEqual(self.blink.region, 'UNKNOWN')
