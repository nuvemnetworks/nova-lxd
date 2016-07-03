# Copyright 2015 Canonical Ltd
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import ddt
import mock

from nova import test

from nova.virt.lxd import operations as container_ops
from nova.virt.lxd import session
import stubs

TEST_INSTANCE_PATH = '/test/instances'


@ddt.ddt
@mock.patch.object(container_ops, 'CONF', stubs.MockConf())
class LXDTestContainerOps(test.NoDBTestCase):
    """LXD Container operations unit tests."""

    def setUp(self):
        super(LXDTestContainerOps, self).setUp()
        self.ml = stubs.lxd_mock()
        lxd_patcher = mock.patch('pylxd.api.API',
                                 mock.Mock(return_value=self.ml))
        lxd_patcher.start()
        self.addCleanup(lxd_patcher.stop)

        self.operations = (
            container_ops.LXDContainerOperations())
        self.mv = mock.MagicMock()
        vif_patcher = mock.patch.object(self.operations,
                                        'vif_driver',
                                        self.mv)
        vif_patcher.start()
        self.addCleanup(vif_patcher.stop)

    def test_reboot_container(self):
        """Test the reboot method. Ensure that the proper
           calls are made when rebooting a continer.
        """
        instance = stubs._fake_instance()
        context = mock.Mock()
        with test.nested(
            mock.patch.object(session.LXDAPISession, 'container_reboot'),

        ) as (container_reboot):
            self.assertEqual(None,
                             self.operations.reboot(context, instance, {},
                                                    None, None, None))
            self.assertTrue(container_reboot)

    def test_power_off(self):
        """Test the power_off method. Ensure that the proper
           calls are made when the container is powered
           off.
        """
        instance = stubs._fake_instance()
        with test.nested(
            mock.patch.object(session.LXDAPISession, 'container_stop')
        ) as (mock_container_stop):
            self.assertEqual(None,
                             self.operations.power_off(instance))
            self.assertTrue(mock_container_stop)

    def test_power_on(self):
        """test the power_on method. Ensure that the proper
           calls are made when the container is powered on.
        """
        instance = stubs._fake_instance()
        network_info = mock.Mock()
        context = mock.Mock()
        block_device_info = mock.Mock()
        with test.nested(
            mock.patch.object(session.LXDAPISession, 'container_start')
        ) as (mock_container_start):
            self.assertEqual(None,
                             self.operations.power_on(context, instance,
                                                      network_info,
                                                      block_device_info))
            self.assertTrue(mock_container_start)

    def test_pause_container(self):
        """Test the pause container method. Ensure that that
           the proper calls are made when pausing the container.
        """
        instance = stubs._fake_instance()
        with test.nested(
            mock.patch.object(session.LXDAPISession, 'container_pause')
        ) as (mock_container_pause):
            self.assertEqual(None,
                             self.operations.pause(instance))
            self.assertTrue(mock_container_pause)

    def test_unpause_container(self):
        """Test the unapuse continaer. Ensure that the proper
           calls are made when unpausing a container.
        """
        instance = stubs._fake_instance()
        with test.nested(
            mock.patch.object(session.LXDAPISession, 'container_unpause')
        ) as (mock_container_unpause):
            self.assertEqual(None,
                             self.operations.unpause(instance))
            self.assertTrue(mock_container_unpause)

    def test_container_suspend(self):
        instance = stubs._fake_instance()
        context = mock.Mock()
        with test.nested(
            mock.patch.object(session.LXDAPISession, 'container_pause')
        ) as (mock_container_suspend):
            self.assertEqual(None,
                             self.operations.suspend(context, instance))
            self.assertTrue(mock_container_suspend)

    def test_container_resume(self):
        instance = stubs._fake_instance()
        context = mock.Mock()
        network_info = mock.Mock()
        with test.nested(
            mock.patch.object(session.LXDAPISession, 'container_unpause')
        ) as (mock_container_resume):
            self.assertEqual(None,
                             self.operations.resume(context, instance,
                                                    network_info))
            self.assertTrue(mock_container_resume)