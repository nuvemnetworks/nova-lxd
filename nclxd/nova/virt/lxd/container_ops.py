# Copyright 2011 Justin Santa Barbara
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

import os
import pwd

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import units

from nova.i18n import _, _LW
from nova import exception
from nova.openstack.common import fileutils
from nova.virt import driver
from nova.virt import hardware
from nova import utils

import container_config
import container_utils
import vif

CONF = cfg.CONF
CONF.import_opt('vif_plugging_timeout', 'nova.virt.driver')
CONF.import_opt('vif_plugging_is_fatal', 'nova.virt.driver')
LOG = logging.getLogger(__name__)

MAX_CONSOLE_BYTES = 100 * units.Ki


class LXDContainerOperations(object):

    def __init__(self, virtapi):
        self.virtapi = virtapi

        self.container_config = container_config.LXDContainerConfig()
        self.container_utils = container_utils.LXDContainerUtils()
        self.container_dir = container_utils.LXDContainerDirectories()
        self.vif_driver = vif.LXDGenericDriver()

    def init_host(self, host):
        return self.container_utils.init_lxd_host(host)

    def list_instances(self):
        return self.container_utils.list_containers()

    def spawn(self, context, instance, image_meta, injected_files,
              admin_password, network_info=None, block_device_info=None):
        msg = ('Spawning container '
               'network_info=%(network_info)s '
               'image_meta=%(image_meta)s '
               'instance=%(instance)s '
               'block_device_info=%(block_device_info)s' %
               {'network_info': network_info,
                'instance': instance,
                'image_meta': image_meta,
                'block_device_info': block_device_info})
        LOG.debug(msg, instance=instance)

        name = instance.uuid
        if self.container_utils.container_defined(instance):
            raise exception.InstanceExists(instance=name)

        self.create_instance(context, instance, image_meta, injected_files,
                             admin_password, network_info, block_device_info)

    def create_instance(self, context, instance, image_meta, injected_files,
                        admin_password, network_info, block_device_info):
        LOG.debug('Creating instance')

        # Ensure the directory exists and is writable
        fileutils.ensure_tree(self.container_dir.get_instance_dir(instance))

        # Check to see if we are using swap.
        swap = driver.block_device_info_get_swap(block_device_info)
        if driver.swap_is_usable(swap):
            msg = _('Swap space is not supported by LXD.')
            raise exception.NovaException(msg)

        # Check to see if ephemeral block devices exist.
        ephemeral_gb = instance.ephemeral_gb
        if ephemeral_gb > 0:
            msg = _('Ephemeral block devices is not supported.')
            raise exception.NovaException(msg)

        container_config = self.container_config.create_container(context,
                                                                  instance, image_meta,
                                                                  injected_files, admin_password,
                                                                  network_info, block_device_info)
        LOG.debug(container_config)
        self.container_utils.container_init(container_config)
        self.start_instance(instance, network_info)

    def start_instance(self, instance, network_info):
        LOG.debug('Staring instance')
        timeout = CONF.vif_plugging_timeout
        # check to see if neutron is ready before
        # doing anything else
        if (not self.container_utils.container_running(instance) and
                utils.is_neutron() and timeout):
            events = self._get_neutron_events(network_info)
        else:
            events = {}

        try:
            with self.virtapi.wait_for_instance_event(
                    instance, events, deadline=timeout,
                    error_callback=self._neutron_failed_callback):
                self.plug_vifs(instance, network_info)
        except exception.VirtualInterfaceCreateException:
            LOG.info(_LW('Failed to connect networking to instance'))

        (state, data) = self.container_utils.container_start(instance)
        self.container_utils.wait_for_container(
            data.get('operation').split('/')[3])

    def plug_vifs(self, instance, network_info):
        for vif in network_info:
            self.vif_driver.plug(instance, vif)

    def unplug_vifs(self, instance, network_info):
        for vif in network_info:
            self.vif_driver.plug(instance, vif)

    def destroy(self, context, instance, network_info, block_device_info=None,
                destroy_disks=True, migrate_data=None):
        self.container_utils.container_destroy(instance)
        self.cleanup(context, instance, network_info, block_device_info)

    def cleanup(self, context, instance, network_info, block_device_info=None,
                destroy_disks=True, migrate_data=None, destroy_vifs=True):
        return self.container_utils.container_cleanup(instance, network_info,
                                                      block_device_info)

    def get_info(self, instance):
        container_info = self.container_utils.container_info(instance)
        return hardware.InstanceInfo(state=container_info,
                                     max_mem_kb=0,
                                     mem_kb=0,
                                     num_cpu=2,
                                     cpu_time_ns=0)

    def get_console_output(self, context, instance):
        LOG.debug('in console output')

        console_log = self.container_dir.get_console_path(instance)
        uid = pwd.getpwuid(os.getuid()).pw_uid
        utils.execute('chown', '%s:%s' % (uid, uid),
                      console_log, run_as_root=True)
        utils.execute('chmod', '755',
                      self.container_dir.get_container_dir(instance),
                      run_as_root=True)
        with open(console_log, 'rb') as fp:
            log_data, remaning = utils.last_bytes(fp,
                                                  MAX_CONSOLE_BYTES)
            return log_data

    def _get_neutron_events(self, network_info):
        return [('network-vif-plugged', vif['id'])
                for vif in network_info if vif.get('active', True) is False]

    def _neutron_failed_callback(self, event_name, instance):
        LOG.error(_LE('Neutron Reported failure on event '
                      '%(event)s for instance %(uuid)s'),
                  {'event': event_name, 'uuid': instance.uuid})
        if CONF.vif_plugging_is_fatal:
            raise exception.VirtualInterfaceCreateException()