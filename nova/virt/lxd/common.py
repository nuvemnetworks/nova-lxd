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
import collections
import os

from nova import conf

from oslo_log import log as logging
LOG = logging.getLogger(__name__)

_InstanceAttributes = collections.namedtuple('InstanceAttributes', [
    'instance_dir', 'console_path', 'storage_path', 'container_path'])


def InstanceAttributes(instance):
    """An instance adapter for nova-lxd specific attributes."""
    instance_dir = os.path.join(conf.CONF.instances_path, instance.name)
    console_path = os.path.join('/var/log/lxd/', instance.name, 'console.log')
    storage_path = os.path.join(instance_dir, 'storage')
    container_path = os.path.join(
        conf.CONF.lxd.root_dir, 'containers', instance.name)
    return _InstanceAttributes(
        instance_dir, console_path, storage_path, container_path)

"""
Pureport - The following functions facilitate finding LXD containers by name
in the event that the instance name template changes in OpenStack.
"""

def get_instance_criteria(instance):
    """Returns the list of possible instance name criteria used to find a container"""

    return [
        instance.name,
        "instance-%08x" % instance.id
    ]

def get_container(client, instance, suffix = ''):
    """Returns the container associated to the specified instance.

    Queries based on multiple possible sets of criteria to support scenarios
    where OpenStack instance name template changes.
    """

    instance_criteria = map(lambda x : x + suffix, get_instance_criteria(instance))

    LOG.info("Instance = {}".format(instance))
    for criteria in instance_criteria:
        try:
            instance = client.containers.get(criteria)
            if instance != None:
                LOG.info("Instance {} found by criteria {}", instance, criteria)
                return instance
        except:
            LOG.warn("Unable to find instance {}".format(criteria), instance=instance)

    return None

def get_rescue_container(client, instance):
    """Returns the rescue container for the specified instance if it exists."""
    return get_container(client, instance, '-rescue')

def get_profile(client, instance):
    """Returns the profile for the specified instance """
    instance_criteria = get_instance_criteria(instance)
    for criteria in instance_criteria:
        try: 
            instance = client.profiles.get(criteria)
            if instance != None:
                LOG.info("Instance {} found by criteria {}", instance, criteria)
                return instance
        except:
            LOG.warn("Unable to find instance {}".format(criteria), instance=instance)

    return None
