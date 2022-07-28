#!/usr/bin/env python3

# Copyright 2021 Canonical Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import mock

import charm
import ops_sunbeam.test_utils as test_utils


class _NovaXenaOperatorCharm(charm.NovaXenaOperatorCharm):

    def __init__(self, framework):
        self.seen_events = []
        super().__init__(framework)

    def _log_event(self, event):
        self.seen_events.append(type(event).__name__)

    def configure_charm(self, event):
        super().configure_charm(event)
        self._log_event(event)

    @property
    def public_ingress_address(self):
        return "nova.juju"


class TestNovaOperatorCharm(test_utils.CharmTestCase):

    PATCHES = []

    @mock.patch(
        'charms.observability_libs.v0.kubernetes_service_patch.'
        'KubernetesServicePatch')
    def setUp(self, mock_patch):
        super().setUp(charm, self.PATCHES)
        self.harness = test_utils.get_harness(
            _NovaXenaOperatorCharm,
            container_calls=self.container_calls)
        self.addCleanup(self.harness.cleanup)
        test_utils.add_complete_ingress_relation(self.harness)
        self.harness.begin()

    def test_pebble_ready_handler(self):
        self.assertEqual(self.harness.charm.seen_events, [])
        test_utils.set_all_pebbles_ready(self.harness)
        self.assertEqual(len(self.harness.charm.seen_events), 3)

    def test_all_relations(self):
        self.harness.set_leader()
        test_utils.set_all_pebbles_ready(self.harness)
        test_utils.add_all_relations(self.harness)

        setup_cmds = [
            ['a2ensite', 'wsgi-nova-api'],
            ['sudo', '-u', 'nova', 'nova-manage', 'api_db', 'sync'],
            ['sudo', '-u', 'nova', 'nova-manage', 'cell_v2', 'map_cell0'],
            ['sudo', '-u', 'nova', 'nova-manage', 'db', 'sync'],
            ['sudo', '-u', 'nova', 'nova-manage', 'cell_v2', 'create_cell',
             '--name', 'cell1', '--verbose'],
        ]
        for cmd in setup_cmds:
            self.assertIn(cmd, self.container_calls.execute['nova-api'])
        config_files = [
            '/etc/apache2/sites-available/wsgi-nova-api.conf',
            '/etc/nova/nova.conf']
        for f in config_files:
            self.check_file('nova-api', f)
