# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""Kubernetes Manifest Builder - Define K8s resources with a fluent Python API.

This example demonstrates how BuilderBase can be used to create
Kubernetes manifests programmatically, with validation and type safety.

Instead of writing error-prone YAML:

    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: nginx
    spec:
      replicas: 3
      ...

You write readable Python:

    k8s = TreeStore(builder=K8sBuilder())
    deploy = k8s.deployment(name='nginx', namespace='web')
    spec = deploy.spec()
    spec.replicas(value=3)
    spec.template().spec().container(name='nginx', image='nginx:1.21').port(value=80)

Benefits:
- IDE autocompletion and type hints
- Validation before deployment
- Reusable components and functions
- No YAML indentation errors
"""

from typing import Any

from genro_treestore import TreeStore
from genro_treestore.builders import BuilderBase, element


class K8sBuilder(BuilderBase):
    """Builder for Kubernetes manifests.

    Provides fluent API for creating K8s resources with validation.
    """

    # ==================== Workload Resources ====================

    @element(children='metadata[1:1], spec[1:1]')
    def deployment(self, target: TreeStore, tag: str, **attr: Any) -> TreeStore:
        """Create a Deployment resource."""
        attr.setdefault('apiVersion', 'apps/v1')
        attr.setdefault('kind', 'Deployment')
        return self.child(target, tag, **attr)

    @element(children='metadata[1:1], spec[1:1]')
    def statefulset(self, target: TreeStore, tag: str, **attr: Any) -> TreeStore:
        """Create a StatefulSet resource."""
        attr.setdefault('apiVersion', 'apps/v1')
        attr.setdefault('kind', 'StatefulSet')
        return self.child(target, tag, **attr)

    @element(children='metadata[1:1], spec[1:1]')
    def daemonset(self, target: TreeStore, tag: str, **attr: Any) -> TreeStore:
        """Create a DaemonSet resource."""
        attr.setdefault('apiVersion', 'apps/v1')
        attr.setdefault('kind', 'DaemonSet')
        return self.child(target, tag, **attr)

    # ==================== Service Resources ====================

    @element(children='metadata[1:1], spec[1:1]')
    def service(self, target: TreeStore, tag: str, **attr: Any) -> TreeStore:
        """Create a Service resource."""
        attr.setdefault('apiVersion', 'v1')
        attr.setdefault('kind', 'Service')
        return self.child(target, tag, **attr)

    @element(children='metadata[1:1], spec[1:1]')
    def ingress(self, target: TreeStore, tag: str, **attr: Any) -> TreeStore:
        """Create an Ingress resource."""
        attr.setdefault('apiVersion', 'networking.k8s.io/v1')
        attr.setdefault('kind', 'Ingress')
        return self.child(target, tag, **attr)

    # ==================== Config Resources ====================

    @element(children='metadata[1:1], data[:1]')
    def configmap(self, target: TreeStore, tag: str, **attr: Any) -> TreeStore:
        """Create a ConfigMap resource."""
        attr.setdefault('apiVersion', 'v1')
        attr.setdefault('kind', 'ConfigMap')
        return self.child(target, tag, **attr)

    @element(children='metadata[1:1], data[:1]')
    def secret(self, target: TreeStore, tag: str, **attr: Any) -> TreeStore:
        """Create a Secret resource."""
        attr.setdefault('apiVersion', 'v1')
        attr.setdefault('kind', 'Secret')
        return self.child(target, tag, **attr)

    # ==================== Metadata ====================

    @element(children='name[:1], namespace[:1], labels[:1], annotations[:1]')
    def metadata(self, target: TreeStore, tag: str, **attr: Any) -> TreeStore:
        """Create metadata section."""
        return self.child(target, tag, **attr)

    @element()
    def name(self, target: TreeStore, tag: str, value: str = '', **attr: Any):
        """Set resource name."""
        return self.child(target, tag, value=value, **attr)

    @element()
    def namespace(self, target: TreeStore, tag: str, value: str = '', **attr: Any):
        """Set resource namespace."""
        return self.child(target, tag, value=value, **attr)

    @element()
    def labels(self, target: TreeStore, tag: str, **attr: Any) -> TreeStore:
        """Create labels section (key-value pairs as attributes)."""
        return self.child(target, tag, **attr)

    @element()
    def annotations(self, target: TreeStore, tag: str, **attr: Any) -> TreeStore:
        """Create annotations section."""
        return self.child(target, tag, **attr)

    # ==================== Spec ====================

    @element(children='replicas[:1], selector[:1], template[:1], container, volumes')
    def spec(self, target: TreeStore, tag: str, **attr: Any) -> TreeStore:
        """Create spec section."""
        return self.child(target, tag, **attr)

    @element()
    def replicas(self, target: TreeStore, tag: str, value: int = 1, **attr: Any):
        """Set replica count."""
        return self.child(target, tag, value=value, **attr)

    @element(children='matchLabels[:1]')
    def selector(self, target: TreeStore, tag: str, **attr: Any) -> TreeStore:
        """Create selector section."""
        return self.child(target, tag, **attr)

    @element()
    def matchLabels(self, target: TreeStore, tag: str, **attr: Any) -> TreeStore:
        """Create matchLabels section."""
        return self.child(target, tag, **attr)

    @element(children='metadata[:1], spec[1:1]')
    def template(self, target: TreeStore, tag: str, **attr: Any) -> TreeStore:
        """Create pod template section."""
        return self.child(target, tag, **attr)

    # ==================== Containers ====================

    @element(children='image[1:1], command[:1], args[:1], env, port, resources[:1], volumeMounts')
    def container(self, target: TreeStore, tag: str, **attr: Any) -> TreeStore:
        """Create a container definition."""
        return self.child(target, tag, **attr)

    @element()
    def image(self, target: TreeStore, tag: str, value: str = '', **attr: Any):
        """Set container image."""
        return self.child(target, tag, value=value, **attr)

    @element()
    def command(self, target: TreeStore, tag: str, **attr: Any) -> TreeStore:
        """Set container command (list of strings)."""
        return self.child(target, tag, **attr)

    @element()
    def args(self, target: TreeStore, tag: str, **attr: Any) -> TreeStore:
        """Set container args (list of strings)."""
        return self.child(target, tag, **attr)

    @element()
    def env(self, target: TreeStore, tag: str, **attr: Any) -> TreeStore:
        """Create environment variable."""
        return self.child(target, tag, **attr)

    @element()
    def port(self, target: TreeStore, tag: str, value: int = 0, **attr: Any):
        """Define a container port."""
        return self.child(target, tag, value=value, **attr)

    @element(children='limits[:1], requests[:1]')
    def resources(self, target: TreeStore, tag: str, **attr: Any) -> TreeStore:
        """Create resources section (limits/requests)."""
        return self.child(target, tag, **attr)

    @element()
    def limits(self, target: TreeStore, tag: str, **attr: Any) -> TreeStore:
        """Set resource limits (cpu, memory as attributes)."""
        return self.child(target, tag, **attr)

    @element()
    def requests(self, target: TreeStore, tag: str, **attr: Any) -> TreeStore:
        """Set resource requests."""
        return self.child(target, tag, **attr)

    # ==================== Volumes ====================

    @element()
    def volumes(self, target: TreeStore, tag: str, **attr: Any) -> TreeStore:
        """Create volumes section."""
        return self.child(target, tag, **attr)

    @element()
    def volumeMounts(self, target: TreeStore, tag: str, **attr: Any) -> TreeStore:
        """Create volume mounts section."""
        return self.child(target, tag, **attr)

    # ==================== Data (ConfigMap/Secret) ====================

    @element()
    def data(self, target: TreeStore, tag: str, **attr: Any) -> TreeStore:
        """Create data section (key-value pairs)."""
        return self.child(target, tag, **attr)


# ==================== Example Usage ====================

if __name__ == '__main__':
    # Create a K8s builder
    k8s = TreeStore(builder=K8sBuilder())

    # Create a Deployment
    deploy = k8s.deployment(name='nginx-deployment')

    # Metadata
    meta = deploy.metadata()
    meta.name(value='nginx')
    meta.namespace(value='web')
    meta.labels(app='nginx', tier='frontend')

    # Spec
    spec = deploy.spec()
    spec.replicas(value=3)

    selector = spec.selector()
    selector.matchLabels(app='nginx')

    template = spec.template()
    tmpl_meta = template.metadata()
    tmpl_meta.labels(app='nginx')

    tmpl_spec = template.spec()
    container = tmpl_spec.container(name='nginx')
    container.image(value='nginx:1.21')
    container.port(value=80, name='http')
    container.resources().limits(cpu='500m', memory='128Mi')

    # Print the structure
    print("Deployment structure:")
    print("=" * 40)

    def show(store, indent=0):
        for node in store.nodes():
            prefix = '  ' * indent
            attrs = {k: v for k, v in node.attr.items() if not k.startswith('_')}
            if node.is_branch:
                attr_str = f' {attrs}' if attrs else ''
                print(f'{prefix}{node.tag or node.label}{attr_str}')
                show(node.value, indent + 1)
            else:
                attr_str = f' {attrs}' if attrs else ''
                print(f'{prefix}{node.tag or node.label}: {node.value}{attr_str}')

    show(k8s)

    # Validate structure
    print("\nValidation:")
    print("=" * 40)
    errors = k8s._builder.check(k8s)
    if errors:
        for err in errors:
            print(f"  ERROR: {err}")
    else:
        print("  All validations passed!")

    # Create a ConfigMap
    print("\n\nConfigMap structure:")
    print("=" * 40)

    k8s2 = TreeStore(builder=K8sBuilder())
    cm = k8s2.configmap()
    cm.metadata().name(value='app-config')
    cm.data(
        DATABASE_URL='postgres://localhost/db',
        LOG_LEVEL='info',
        CACHE_TTL='3600'
    )

    show(k8s2)
