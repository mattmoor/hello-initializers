"""A controller for initializing resources."""

import hashlib
import httplib
import json
from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException
import logging
import os
import time

DOMAIN = "experimental.mattmoor.io"
ALL_NAMESPACES = ""
ANNOTATION = DOMAIN + "/removeme"

def main():
    config.load_incluster_config()

    batch = client.BatchV1Api()

    def needs_initialization(obj):
        # https://kubernetes.io/docs/admin/extensible-admission-controllers/\
        #   #how-are-initializers-triggered
        initializers = obj.metadata.initializers
        if not initializers:
            return False
        pending = initializers.pending
        if not pending:
            return False
        return pending[0].name == DOMAIN

    def wants_initialization(obj):
        for (k, v) in (obj.metadata.annotations or {}).iteritems():
            if k == ANNOTATION:
                logging.error("Saw annotation: %s: %s", k, v)
                return True
        return False

    def initialize(obj):
        # Remove the annotation to initialize things.
        obj.metadata.annotations.pop(ANNOTATION, None)
        initialized(obj)

    def initialized(obj):
        # Remove the first initializer (which is us).
        obj.metadata.initializers.pending.pop(0)
        batch.replace_namespaced_job(obj.metadata.name, obj.metadata.namespace, obj)
        logging.error("Initialized: %s", obj.metadata.name)

    resource_version = ""
    while True:
        stream = watch.Watch().stream(
            batch.list_namespaced_job, ALL_NAMESPACES, resource_version=resource_version,
            # Include uninitialized objects, so that we can initialize them.
            include_uninitialized=True)

        for event in stream:
            obj = event["object"]
            logging.error("Got %s for %s", event["type"], obj.metadata.name)

            if needs_initialization(obj):
                if wants_initialization(obj):
                    initialize(obj)
                else:
                    initialized(obj)

            # TODO(mattmoor): Add logic for recovering if the controller crashes mid-init.

if __name__ == "__main__":
    main()
