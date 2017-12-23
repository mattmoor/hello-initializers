"""A controller for initializing resources."""

import hashlib
import httplib
import httplib2
import json
from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException
import logging
import os
import time

from containerregistry.client import docker_name
from containerregistry.client import docker_creds
from containerregistry.client.v2_2 import docker_image

DOMAIN = "experimental.mattmoor.io"
ALL_NAMESPACES = ""

def main():
    config.load_incluster_config()

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
        # The types of resources on which this operates universally
        # contain image references.
        return True

    def resolve_container_ref(name):
        try:
            # It might also be a digest, in which case there is nothing to do.
            name = docker_name.Tag(name, strict=False)

            with docker_image.FromRegistry(
                    name, docker_creds.Anonymous(), httplib2.Http()) as img:
                return "{repo}@{digest}".format(
                    repo=name.as_repository(),
                    digest=img.digest())
        except docker_name.BadNameException:
            return name
        except:
            logging.exception("Unexpected error resolving name: %s", name)
            return name

    def resolve_pod_spec(pod_template):
        for c in (pod_template.spec.init_containers or []):
            c.image = resolve_container_ref(c.image)

        for c in (pod_template.spec.containers or []):
            c.image = resolve_container_ref(c.image)

    def initialize_type(list_type, replace_type):
        def initialized(obj):
            # Remove the first initializer (which is us).
            obj.metadata.initializers.pending.pop(0)
            replace_type(obj.metadata.name, obj.metadata.namespace, obj)
            logging.error("Initialized: %s", obj.metadata.name)

        def initialize(obj):
            resolve_pod_spec(obj.spec.template)
            logging.error("Initialized spec: %s", obj)
            initialized(obj)

        resource_version = ""
        while True:
            stream = watch.Watch().stream(
                list_type, ALL_NAMESPACES, resource_version=resource_version,
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

    # batch = client.BatchV1Api()
    # initialize_type(batch.list_namespaced_job, batch.replace_namespaced_job)

    # apps = client.AppsV1beta1Api()
    # initialize_type(apps.list_namespaced_deployment, apps.replace_namespaced_deployment)

    extensions = client.ExtensionsV1beta1Api()
    initialize_type(extensions.list_namespaced_replica_set, extensions.replace_namespaced_replica_set)


if __name__ == "__main__":
    main()
