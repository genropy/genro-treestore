# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""Kubernetes Manifest Builder - Define K8s resources with a fluent Python API.

This example demonstrates how TreeStoreBuilder can be used to create
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

    deploy = k8s.deployment('nginx', namespace='web')
    deploy.replicas(3)
    deploy.container('nginx', image='nginx:1.21').port(80)

Benefits:
- IDE autocompletion and type hints
- Validation before deployment
- Reusable components and functions
- No YAML indentation errors
"""

from genro_treestore import TreeStoreBuilder, Grammar, element


class K8sGrammar(Grammar):
    """Grammar defining valid Kubernetes resource structures."""

    # ==================== Resource Types ====================

    @property
    def workloads(self):
        """Workload resources."""
        return dict(
            tag='deployment,statefulset,daemonset,job,cronjob',
            valid_children={
                'metadata': '1',      # exactly one
                'spec': '1',          # exactly one
            }
        )

    @property
    def services(self):
        """Service resources."""
        return dict(
            tag='service,ingress',
            valid_children={
                'metadata': '1',
                'spec': '1',
            }
        )

    @property
    def config(self):
        """Configuration resources."""
        return dict(
            tag='configmap,secret',
            valid_children={
                'metadata': '1',
                'data': '?',          # zero or one
            }
        )

    # ==================== Common Elements ====================

    @property
    def metadata_elements(self):
        """Metadata sub-elements."""
        return dict(
            tag='name,namespace,labels,annotations',
        )

    @property
    def spec_elements(self):
        """Spec sub-elements."""
        return dict(
            tag='replicas,selector,template,containers,volumes,'
                'ports,type,cluster_ip,load_balancer_ip',
        )

    @property
    def container_elements(self):
        """Container configuration elements."""
        return dict(
            tag='container,init_container',
            valid_children={
                'image,command,args,env,env_from,ports,'
                'resources,volume_mounts,liveness_probe,'
                'readiness_probe,security_context': '*'
            }
        )


class K8sBuilder(TreeStoreBuilder):
    """Kubernetes manifest builder with fluent API.

    Example:
        k8s = K8sBuilder()

        # Create a Deployment
        deploy = k8s.deployment('nginx', namespace='web')
        deploy.replicas(3)
        container = deploy.container('nginx', image='nginx:1.21')
        container.port(80)
        container.resources(cpu='100m', memory='128Mi')

        # Create a Service
        svc = k8s.service('nginx', namespace='web')
        svc.port(80, target_port=80)
        svc.type('ClusterIP')

        # Export
        print(k8s.to_yaml())
    """

    def __init__(self, **kw):
        kw.setdefault('grammar', K8sGrammar)
        super().__init__(**kw)

    # ==================== Workload Resources ====================

    def deployment(self, name, namespace='default', **labels):
        """Create a Deployment resource.

        Args:
            name: Deployment name
            namespace: Kubernetes namespace
            **labels: Labels to apply

        Returns:
            DeploymentBuilder for chaining
        """
        deploy = self.child('deployment', label=name,
                           api_version='apps/v1', kind='Deployment')
        deploy.child('metadata', name=name, namespace=namespace, labels=labels or {'app': name})
        spec = deploy.child('spec')
        return DeploymentBuilder(spec, name, labels or {'app': name})

    def statefulset(self, name, namespace='default', **labels):
        """Create a StatefulSet resource."""
        sts = self.child('statefulset', label=name,
                        api_version='apps/v1', kind='StatefulSet')
        sts.child('metadata', name=name, namespace=namespace, labels=labels or {'app': name})
        spec = sts.child('spec')
        return StatefulSetBuilder(spec, name, labels or {'app': name})

    def daemonset(self, name, namespace='default', **labels):
        """Create a DaemonSet resource."""
        ds = self.child('daemonset', label=name,
                       api_version='apps/v1', kind='DaemonSet')
        ds.child('metadata', name=name, namespace=namespace, labels=labels or {'app': name})
        spec = ds.child('spec')
        return DaemonSetBuilder(spec, name, labels or {'app': name})

    def job(self, name, namespace='default', **labels):
        """Create a Job resource."""
        job = self.child('job', label=name,
                        api_version='batch/v1', kind='Job')
        job.child('metadata', name=name, namespace=namespace, labels=labels or {'app': name})
        spec = job.child('spec')
        return JobBuilder(spec, name, labels or {'app': name})

    def cronjob(self, name, schedule, namespace='default', **labels):
        """Create a CronJob resource.

        Args:
            name: CronJob name
            schedule: Cron schedule expression (e.g., '0 * * * *')
            namespace: Kubernetes namespace
            **labels: Labels to apply
        """
        cj = self.child('cronjob', label=name,
                       api_version='batch/v1', kind='CronJob')
        cj.child('metadata', name=name, namespace=namespace, labels=labels or {'app': name})
        spec = cj.child('spec', schedule=schedule)
        return CronJobBuilder(spec, name, labels or {'app': name})

    # ==================== Service Resources ====================

    def service(self, name, namespace='default', **labels):
        """Create a Service resource.

        Args:
            name: Service name
            namespace: Kubernetes namespace
            **labels: Labels/selector

        Returns:
            ServiceBuilder for chaining
        """
        svc = self.child('service', label=name,
                        api_version='v1', kind='Service')
        svc.child('metadata', name=name, namespace=namespace, labels=labels or {'app': name})
        spec = svc.child('spec')
        return ServiceBuilder(spec, labels or {'app': name})

    def ingress(self, name, namespace='default', **annotations):
        """Create an Ingress resource."""
        ing = self.child('ingress', label=name,
                        api_version='networking.k8s.io/v1', kind='Ingress')
        ing.child('metadata', name=name, namespace=namespace, annotations=annotations)
        spec = ing.child('spec')
        return IngressBuilder(spec)

    # ==================== Config Resources ====================

    def configmap(self, name, namespace='default', **data):
        """Create a ConfigMap resource.

        Args:
            name: ConfigMap name
            namespace: Kubernetes namespace
            **data: Key-value data to store
        """
        cm = self.child('configmap', label=name,
                       api_version='v1', kind='ConfigMap')
        cm.child('metadata', name=name, namespace=namespace)
        if data:
            cm.child('data', **data)
        return ConfigMapBuilder(cm)

    def secret(self, name, namespace='default', type='Opaque', **data):
        """Create a Secret resource.

        Args:
            name: Secret name
            namespace: Kubernetes namespace
            type: Secret type (Opaque, kubernetes.io/tls, etc.)
            **data: Key-value data (will be base64 encoded)
        """
        sec = self.child('secret', label=name,
                        api_version='v1', kind='Secret', type=type)
        sec.child('metadata', name=name, namespace=namespace)
        if data:
            sec.child('data', **data)
        return SecretBuilder(sec)

    # ==================== Export ====================

    def to_yaml(self):
        """Export all resources as YAML."""
        import yaml

        documents = []
        for node in self._order:
            doc = self._node_to_k8s(node)
            documents.append(doc)

        return '---\n'.join(yaml.dump(doc, default_flow_style=False) for doc in documents)

    def _node_to_k8s(self, node):
        """Convert a resource node to K8s dict format."""
        result = {
            'apiVersion': node.attr.get('api_version', 'v1'),
            'kind': node.attr.get('kind', node.tag.title()),
        }

        if node.is_branch:
            for child in node.value._order:
                key = self._to_camel_case(child.label)
                if child.label in ('metadata', 'spec', 'data'):
                    result[key] = self._flatten_node(child)
                else:
                    result[key] = child.value

        return result

    def _flatten_node(self, node):
        """Flatten a node to a dict."""
        if node.is_leaf:
            return node.value

        result = dict(node.attr)
        if node.is_branch:
            for child in node.value._order:
                key = self._to_camel_case(child.label)
                if child.is_branch:
                    # Check if it's a list-like structure (containers, ports, etc.)
                    if child.label in ('containers', 'init_containers', 'ports',
                                      'volumes', 'volume_mounts', 'env', 'rules'):
                        result[key] = [self._flatten_node(item) for item in child.value._order]
                    else:
                        result[key] = self._flatten_node(child)
                else:
                    result[key] = child.value

        # Clean up internal attributes
        result.pop('_tag', None)
        return result

    def _to_camel_case(self, snake_str):
        """Convert snake_case to camelCase."""
        components = snake_str.split('_')
        return components[0] + ''.join(x.title() for x in components[1:])


# ==================== Resource Builders ====================

class WorkloadBuilder:
    """Base class for workload builders (Deployment, StatefulSet, etc.)."""

    def __init__(self, spec, name, labels):
        self._spec = spec
        self._name = name
        self._labels = labels
        self._template = None

    def replicas(self, count):
        """Set the number of replicas."""
        self._spec.child('replicas', value=count)
        return self

    def selector(self, **match_labels):
        """Set the pod selector."""
        labels = match_labels or self._labels
        self._spec.child('selector', match_labels=labels)
        return self

    def _ensure_template(self):
        """Ensure pod template exists."""
        if self._template is None:
            template = self._spec.child('template')
            template.child('metadata', labels=self._labels)
            self._template = template.child('spec')
        return self._template

    def container(self, name, image, **attr):
        """Add a container to the pod.

        Args:
            name: Container name
            image: Container image
            **attr: Additional container attributes

        Returns:
            ContainerBuilder for chaining
        """
        template = self._ensure_template()
        containers = template.get('containers_0')
        if containers is None:
            containers = template.child('containers')

        container = containers.child('container', label=name, name=name, image=image, **attr)
        return ContainerBuilder(container)

    def init_container(self, name, image, **attr):
        """Add an init container to the pod."""
        template = self._ensure_template()
        init_containers = template.get('init_containers_0')
        if init_containers is None:
            init_containers = template.child('init_containers')

        container = init_containers.child('init_container', label=name, name=name, image=image, **attr)
        return ContainerBuilder(container)

    def volume(self, name, **source):
        """Add a volume to the pod.

        Args:
            name: Volume name
            **source: Volume source (config_map, secret, pvc, empty_dir, etc.)

        Example:
            deploy.volume('config', config_map='nginx-config')
            deploy.volume('data', pvc='data-pvc')
            deploy.volume('tmp', empty_dir={})
        """
        template = self._ensure_template()
        volumes = template.get('volumes_0')
        if volumes is None:
            volumes = template.child('volumes')

        volumes.child('volume', label=name, name=name, **source)
        return self

    def service_account(self, name):
        """Set the service account."""
        template = self._ensure_template()
        template.child('service_account_name', value=name)
        return self

    def node_selector(self, **labels):
        """Set node selector."""
        template = self._ensure_template()
        template.child('node_selector', **labels)
        return self

    def toleration(self, key, operator='Equal', value=None, effect=None):
        """Add a toleration."""
        template = self._ensure_template()
        tolerations = template.get('tolerations_0')
        if tolerations is None:
            tolerations = template.child('tolerations')

        tol = {'key': key, 'operator': operator}
        if value:
            tol['value'] = value
        if effect:
            tol['effect'] = effect

        tolerations.child('toleration', **tol)
        return self


class DeploymentBuilder(WorkloadBuilder):
    """Deployment-specific builder."""

    def strategy(self, type='RollingUpdate', max_surge='25%', max_unavailable='25%'):
        """Set deployment strategy."""
        self._spec.child('strategy', type=type,
                        rolling_update={'maxSurge': max_surge, 'maxUnavailable': max_unavailable})
        return self

    def min_ready_seconds(self, seconds):
        """Set minimum ready seconds."""
        self._spec.child('min_ready_seconds', value=seconds)
        return self


class StatefulSetBuilder(WorkloadBuilder):
    """StatefulSet-specific builder."""

    def service_name(self, name):
        """Set the governing service name."""
        self._spec.child('service_name', value=name)
        return self

    def volume_claim_template(self, name, storage, storage_class=None, access_modes=None):
        """Add a volume claim template."""
        vcts = self._spec.get('volume_claim_templates_0')
        if vcts is None:
            vcts = self._spec.child('volume_claim_templates')

        vct = vcts.child('vct', label=name)
        vct.child('metadata', name=name)
        spec = vct.child('spec')
        spec.child('access_modes', value=access_modes or ['ReadWriteOnce'])
        if storage_class:
            spec.child('storage_class_name', value=storage_class)
        spec.child('resources', requests={'storage': storage})
        return self


class DaemonSetBuilder(WorkloadBuilder):
    """DaemonSet-specific builder."""

    def update_strategy(self, type='RollingUpdate', max_unavailable=1):
        """Set update strategy."""
        self._spec.child('update_strategy', type=type, max_unavailable=max_unavailable)
        return self


class JobBuilder(WorkloadBuilder):
    """Job-specific builder."""

    def backoff_limit(self, limit):
        """Set backoff limit."""
        self._spec.child('backoff_limit', value=limit)
        return self

    def completions(self, count):
        """Set number of completions."""
        self._spec.child('completions', value=count)
        return self

    def parallelism(self, count):
        """Set parallelism."""
        self._spec.child('parallelism', value=count)
        return self

    def ttl_seconds_after_finished(self, seconds):
        """Set TTL after job finishes."""
        self._spec.child('ttl_seconds_after_finished', value=seconds)
        return self


class CronJobBuilder:
    """CronJob-specific builder."""

    def __init__(self, spec, name, labels):
        self._spec = spec
        self._name = name
        self._labels = labels
        self._job_template = None

    def concurrency_policy(self, policy):
        """Set concurrency policy (Allow, Forbid, Replace)."""
        self._spec.child('concurrency_policy', value=policy)
        return self

    def suspend(self, suspended=True):
        """Suspend the CronJob."""
        self._spec.child('suspend', value=suspended)
        return self

    def job(self):
        """Access the job template builder."""
        if self._job_template is None:
            jt = self._spec.child('job_template')
            spec = jt.child('spec')
            self._job_template = JobBuilder(spec, self._name, self._labels)
        return self._job_template


class ContainerBuilder:
    """Container configuration builder."""

    def __init__(self, container):
        self._container = container

    def command(self, *args):
        """Set container command."""
        self._container.child('command', value=list(args))
        return self

    def args(self, *args):
        """Set container arguments."""
        self._container.child('args', value=list(args))
        return self

    def port(self, container_port, name=None, protocol='TCP'):
        """Add a container port.

        Args:
            container_port: Port number
            name: Optional port name
            protocol: Protocol (TCP, UDP)
        """
        ports = self._container.get('ports_0')
        if ports is None:
            ports = self._container.child('ports')

        port_spec = {'containerPort': container_port, 'protocol': protocol}
        if name:
            port_spec['name'] = name

        ports.child('port', **port_spec)
        return self

    def env(self, name, value=None, value_from=None):
        """Add an environment variable.

        Args:
            name: Variable name
            value: Direct value
            value_from: Value from (secret, configmap, field)

        Example:
            container.env('DEBUG', 'true')
            container.env('DB_PASSWORD', value_from={'secretKeyRef': {'name': 'db', 'key': 'password'}})
        """
        envs = self._container.get('env_0')
        if envs is None:
            envs = self._container.child('env')

        env_spec = {'name': name}
        if value is not None:
            env_spec['value'] = str(value)
        if value_from:
            env_spec['valueFrom'] = value_from

        envs.child('env_var', **env_spec)
        return self

    def env_from_secret(self, name, secret_name, key):
        """Add env variable from a secret."""
        return self.env(name, value_from={
            'secretKeyRef': {'name': secret_name, 'key': key}
        })

    def env_from_configmap(self, name, configmap_name, key):
        """Add env variable from a configmap."""
        return self.env(name, value_from={
            'configMapKeyRef': {'name': configmap_name, 'key': key}
        })

    def resources(self, cpu=None, memory=None, cpu_limit=None, memory_limit=None):
        """Set resource requests and limits.

        Args:
            cpu: CPU request (e.g., '100m', '0.5')
            memory: Memory request (e.g., '128Mi', '1Gi')
            cpu_limit: CPU limit
            memory_limit: Memory limit
        """
        resources = {}
        requests = {}
        limits = {}

        if cpu:
            requests['cpu'] = cpu
        if memory:
            requests['memory'] = memory
        if cpu_limit:
            limits['cpu'] = cpu_limit
        if memory_limit:
            limits['memory'] = memory_limit

        if requests:
            resources['requests'] = requests
        if limits:
            resources['limits'] = limits
        if not limits and requests:
            resources['limits'] = requests.copy()

        self._container.child('resources', **resources)
        return self

    def volume_mount(self, name, mount_path, sub_path=None, read_only=False):
        """Mount a volume.

        Args:
            name: Volume name (must match pod volume)
            mount_path: Mount path in container
            sub_path: Optional sub-path within volume
            read_only: Mount as read-only
        """
        mounts = self._container.get('volume_mounts_0')
        if mounts is None:
            mounts = self._container.child('volume_mounts')

        mount = {'name': name, 'mountPath': mount_path}
        if sub_path:
            mount['subPath'] = sub_path
        if read_only:
            mount['readOnly'] = True

        mounts.child('mount', **mount)
        return self

    def liveness_probe(self, http_get=None, exec_command=None, tcp_socket=None,
                       initial_delay=0, period=10, timeout=1, failure_threshold=3):
        """Configure liveness probe."""
        probe = {
            'initialDelaySeconds': initial_delay,
            'periodSeconds': period,
            'timeoutSeconds': timeout,
            'failureThreshold': failure_threshold,
        }
        if http_get:
            probe['httpGet'] = http_get
        elif exec_command:
            probe['exec'] = {'command': exec_command}
        elif tcp_socket:
            probe['tcpSocket'] = tcp_socket

        self._container.child('liveness_probe', **probe)
        return self

    def readiness_probe(self, http_get=None, exec_command=None, tcp_socket=None,
                        initial_delay=0, period=10, timeout=1, success_threshold=1):
        """Configure readiness probe."""
        probe = {
            'initialDelaySeconds': initial_delay,
            'periodSeconds': period,
            'timeoutSeconds': timeout,
            'successThreshold': success_threshold,
        }
        if http_get:
            probe['httpGet'] = http_get
        elif exec_command:
            probe['exec'] = {'command': exec_command}
        elif tcp_socket:
            probe['tcpSocket'] = tcp_socket

        self._container.child('readiness_probe', **probe)
        return self

    def security_context(self, run_as_user=None, run_as_group=None,
                         run_as_non_root=None, read_only_root_filesystem=None,
                         privileged=None):
        """Set container security context."""
        ctx = {}
        if run_as_user is not None:
            ctx['runAsUser'] = run_as_user
        if run_as_group is not None:
            ctx['runAsGroup'] = run_as_group
        if run_as_non_root is not None:
            ctx['runAsNonRoot'] = run_as_non_root
        if read_only_root_filesystem is not None:
            ctx['readOnlyRootFilesystem'] = read_only_root_filesystem
        if privileged is not None:
            ctx['privileged'] = privileged

        self._container.child('security_context', **ctx)
        return self


class ServiceBuilder:
    """Service configuration builder."""

    def __init__(self, spec, selector):
        self._spec = spec
        self._selector = selector
        self._spec.child('selector', **selector)

    def port(self, port, target_port=None, name=None, protocol='TCP', node_port=None):
        """Add a service port.

        Args:
            port: Service port
            target_port: Target port on pods (defaults to port)
            name: Port name (required if multiple ports)
            protocol: Protocol (TCP, UDP)
            node_port: Node port (for NodePort/LoadBalancer services)
        """
        ports = self._spec.get('ports_0')
        if ports is None:
            ports = self._spec.child('ports')

        port_spec = {
            'port': port,
            'targetPort': target_port or port,
            'protocol': protocol,
        }
        if name:
            port_spec['name'] = name
        if node_port:
            port_spec['nodePort'] = node_port

        ports.child('port', **port_spec)
        return self

    def type(self, service_type):
        """Set service type (ClusterIP, NodePort, LoadBalancer, ExternalName)."""
        self._spec.child('type', value=service_type)
        return self

    def cluster_ip(self, ip):
        """Set cluster IP (or 'None' for headless)."""
        self._spec.child('cluster_ip', value=ip)
        return self

    def external_traffic_policy(self, policy):
        """Set external traffic policy (Cluster, Local)."""
        self._spec.child('external_traffic_policy', value=policy)
        return self

    def load_balancer_ip(self, ip):
        """Set load balancer IP."""
        self._spec.child('load_balancer_ip', value=ip)
        return self


class IngressBuilder:
    """Ingress configuration builder."""

    def __init__(self, spec):
        self._spec = spec

    def tls(self, hosts, secret_name):
        """Add TLS configuration."""
        tls = self._spec.get('tls_0')
        if tls is None:
            tls = self._spec.child('tls')

        tls.child('tls_config', hosts=hosts, secret_name=secret_name)
        return self

    def rule(self, host):
        """Add an ingress rule for a host.

        Returns:
            IngressRuleBuilder for adding paths
        """
        rules = self._spec.get('rules_0')
        if rules is None:
            rules = self._spec.child('rules')

        rule = rules.child('rule', host=host)
        http = rule.child('http')
        paths = http.child('paths')
        return IngressRuleBuilder(paths)

    def default_backend(self, service_name, service_port):
        """Set default backend."""
        self._spec.child('default_backend', service={
            'name': service_name,
            'port': {'number': service_port}
        })
        return self


class IngressRuleBuilder:
    """Ingress rule path builder."""

    def __init__(self, paths):
        self._paths = paths

    def path(self, path, service_name, service_port, path_type='Prefix'):
        """Add a path to the rule.

        Args:
            path: URL path
            service_name: Backend service name
            service_port: Backend service port
            path_type: Path type (Prefix, Exact, ImplementationSpecific)
        """
        self._paths.child('path', path=path, path_type=path_type, backend={
            'service': {
                'name': service_name,
                'port': {'number': service_port}
            }
        })
        return self


class ConfigMapBuilder:
    """ConfigMap builder."""

    def __init__(self, cm):
        self._cm = cm

    def data(self, **items):
        """Add data items."""
        data = self._cm.get('data_0')
        if data is None:
            data = self._cm.child('data')
        for k, v in items.items():
            data.child('item', label=k, value=v)
        return self

    def from_file(self, key, content):
        """Add file content."""
        return self.data(**{key: content})


class SecretBuilder:
    """Secret builder."""

    def __init__(self, secret):
        self._secret = secret

    def data(self, **items):
        """Add data items (will be base64 encoded)."""
        import base64
        data = self._secret.get('data_0')
        if data is None:
            data = self._secret.child('data')
        for k, v in items.items():
            encoded = base64.b64encode(v.encode()).decode() if isinstance(v, str) else v
            data.child('item', label=k, value=encoded)
        return self

    def string_data(self, **items):
        """Add string data items (Kubernetes will encode them)."""
        data = self._secret.get('string_data_0')
        if data is None:
            data = self._secret.child('string_data')
        for k, v in items.items():
            data.child('item', label=k, value=v)
        return self


# ==================== Demo ====================

if __name__ == '__main__':
    k8s = K8sBuilder()

    # Create a Deployment
    print("Creating Deployment...")
    deploy = k8s.deployment('nginx', namespace='web', tier='frontend')
    deploy.replicas(3)
    deploy.selector(app='nginx')
    deploy.strategy(type='RollingUpdate', max_surge='1', max_unavailable='0')

    # Main container
    nginx = deploy.container('nginx', image='nginx:1.21-alpine')
    nginx.port(80, name='http')
    nginx.port(443, name='https')
    nginx.resources(cpu='100m', memory='128Mi', cpu_limit='500m', memory_limit='512Mi')
    nginx.env('NGINX_HOST', 'localhost')
    nginx.env_from_secret('TLS_KEY', 'nginx-tls', 'tls.key')
    nginx.volume_mount('config', '/etc/nginx/conf.d', read_only=True)
    nginx.volume_mount('cache', '/var/cache/nginx')
    nginx.liveness_probe(http_get={'path': '/health', 'port': 80}, initial_delay=10)
    nginx.readiness_probe(http_get={'path': '/ready', 'port': 80}, initial_delay=5)
    nginx.security_context(run_as_non_root=True, read_only_root_filesystem=True)

    # Volumes
    deploy.volume('config', config_map='nginx-config')
    deploy.volume('cache', empty_dir={})

    # Create a Service
    print("Creating Service...")
    svc = k8s.service('nginx', namespace='web')
    svc.port(80, target_port=80, name='http')
    svc.port(443, target_port=443, name='https')
    svc.type('LoadBalancer')

    # Create an Ingress
    print("Creating Ingress...")
    ing = k8s.ingress('nginx', namespace='web',
                      **{'kubernetes.io/ingress.class': 'nginx'})
    ing.tls(['myapp.example.com'], 'nginx-tls')
    rule = ing.rule('myapp.example.com')
    rule.path('/', 'nginx', 80)
    rule.path('/api', 'api-service', 8080)

    # Create ConfigMap
    print("Creating ConfigMap...")
    k8s.configmap('nginx-config', namespace='web',
                  **{'default.conf': '''
server {
    listen 80;
    server_name localhost;
    location / {
        root /usr/share/nginx/html;
    }
}
'''})

    # Create Secret
    print("Creating Secret...")
    secret = k8s.secret('nginx-tls', namespace='web', type='kubernetes.io/tls')
    secret.string_data(**{
        'tls.crt': '-----BEGIN CERTIFICATE-----\n...',
        'tls.key': '-----BEGIN PRIVATE KEY-----\n...',
    })

    # Export to YAML
    print("\n" + "=" * 60)
    print("Generated Kubernetes Manifests")
    print("=" * 60 + "\n")

    try:
        print(k8s.to_yaml())
    except ImportError:
        print("(Install PyYAML to see YAML output: pip install pyyaml)")
        print("\nStructure:")
        for path, node in k8s.walk():
            indent = "  " * path.count('.')
            print(f"{indent}{node.label}: {node.value if node.is_leaf else ''}")
