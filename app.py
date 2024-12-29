from flask import Flask, render_template, request, jsonify
from kubernetes import client, config
import re

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/get_namespaces")
def get_namespaces():
    try:
        config.load_incluster_config()
        v1 = client.CoreV1Api()
        excluded_ns = ["kube-node-lease", "kube-public", "kube-system"]
        namespaces = [
            ns.metadata.name
            for ns in v1.list_namespace().items
            if ns.metadata.name not in excluded_ns
        ]
        return jsonify({"namespaces": namespaces})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/deploy_app", methods=["POST"])
def deploy_app():
    try:
        data = request.get_json()
        namespace = data.get("namespace")
        image = data.get("image")
        port = data.get("port")

        if not re.match(r"^[\w\-\.]+/[\w\-\.]+:[\w\-\.]+$", image):
            return jsonify(
                {"error": "Invalid image format. Use: repository/image:tag"}
            ), 400

        if not port.isdigit() or not (1 <= int(port) <= 65535):
            return jsonify({"error": "Port must be between 1 and 65535"}), 400

        config.load_incluster_config()
        apps_v1 = client.AppsV1Api()
        v1 = client.CoreV1Api()

        # Create deployment
        deployment = client.V1Deployment(
            metadata=client.V1ObjectMeta(name=f"app-deployment-{namespace}"),
            spec=client.V1DeploymentSpec(
                replicas=1,
                selector=client.V1LabelSelector(match_labels={"app": "web"}),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(labels={"app": "web"}),
                    spec=client.V1PodSpec(
                        containers=[
                            client.V1Container(
                                name="web",
                                image=image,
                                ports=[
                                    client.V1ContainerPort(container_port=int(port))
                                ],
                            )
                        ]
                    ),
                ),
            ),
        )

        # Create service
        service = client.V1Service(
            metadata=client.V1ObjectMeta(name="app-service"),
            spec=client.V1ServiceSpec(
                type="NodePort",
                ports=[client.V1ServicePort(port=int(port), target_port=int(port))],
                selector={"app": "web"},
            ),
        )

        apps_v1.create_namespaced_deployment(namespace=namespace, body=deployment)
        v1.create_namespaced_service(namespace=namespace, body=service)

        return jsonify({"message": "Application deployed successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/create_namespace", methods=["POST"])
def create_namespace():
    try:
        data = request.get_json()
        namespace = data.get("namespace")

        config.load_incluster_config()
        v1 = client.CoreV1Api()

        existing_namespaces = [ns.metadata.name for ns in v1.list_namespace().items]
        if namespace in existing_namespaces:
            return jsonify({"error": "Namespace already exists"}), 400

        body = client.V1Namespace(metadata=client.V1ObjectMeta(name=namespace))
        v1.create_namespace(body=body)

        return jsonify({"message": "Namespace created successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/remove_namespace/<namespace>")
def remove_namespace(namespace):
    try:
        delete_ns = request.args.get("delete_namespace", "false").lower() == "true"

        if namespace == "default" and delete_ns:
            return jsonify({"error": "Cannot delete default namespace"}), 400

        config.load_incluster_config()
        v1 = client.CoreV1Api()
        apps_v1 = client.AppsV1Api()

        # Delete all resources
        apps_v1.delete_collection_namespaced_deployment(namespace=namespace)
        v1.delete_collection_namespaced_service(namespace=namespace)
        v1.delete_collection_namespaced_pod(namespace=namespace)

        if delete_ns and namespace != "default":
            v1.delete_namespace(name=namespace)
            return jsonify(
                {"message": f"Namespace {namespace} and all resources removed"}
            )

        return jsonify({"message": f"All resources in namespace {namespace} removed"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/reset_namespace/<namespace>")
def reset_namespace(namespace):
    try:
        config.load_incluster_config()
        v1 = client.CoreV1Api()
        v1.delete_collection_namespaced_pod(namespace=namespace)
        return jsonify({"message": f"Namespace {namespace} reset"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/get_pods/<namespace>")
def get_pods(namespace):
    try:
        config.load_incluster_config()
        v1 = client.CoreV1Api()
        pod_list = v1.list_namespaced_pod(namespace)
        pods = []
        for pod in pod_list.items:
            container_statuses = pod.status.container_statuses or []
            restart_count = sum(
                container.restart_count for container in container_statuses
            )
            ready_containers = sum(
                1 for container in container_statuses if container.ready
            )
            total_containers = len(container_statuses)
            ready_status = f"{ready_containers}/{total_containers}"

            # Get image tag from the first container
            image_tag = "N/A"
            if container_statuses:
                image = container_statuses[0].image
                if ":" in image:
                    image_tag = image.split(":")[-1]

            pods.append(
                {
                    "name": pod.metadata.name,
                    "ready": ready_status,
                    "status": pod.status.phase,
                    "restarts": restart_count,
                    "age": pod.metadata.creation_timestamp.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    "image_tag": image_tag,
                }
            )
        return jsonify({"pods": pods})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/get_services/<namespace>")
def get_services(namespace):
    try:
        config.load_incluster_config()
        v1 = client.CoreV1Api()
        svc_list = v1.list_namespaced_service(namespace)
        services = []
        for svc in svc_list.items:
            ports = []
            for port in svc.spec.ports:
                port_info = f"{port.port}"
                if port.node_port:
                    port_info += f":{port.node_port}"
                ports.append(port_info)

            services.append(
                {
                    "name": svc.metadata.name,
                    "type": svc.spec.type,
                    "cluster_ip": svc.spec.cluster_ip,
                    "ports": ", ".join(ports),
                    "age": svc.metadata.creation_timestamp.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                }
            )
        return jsonify({"services": services})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
