# kubectl-confirmation
A plugin that prompts users for permission before executing kubectl commands or modifying custom resources.

## Prerequisites
- Go must be installed.
- Kubernetes must be installed and kubectl must be available.

## Install / Uninstall

- Generating the kubectl-confirmation binary file
   ```
   $ make build
   ```

- Install binary files to $GOBIN or $GOPATH/bin
   ```
   $ make install
   ```
   - If $GOBIN is not set, it will be installed to $GOPATH/bin.

- To uninstall
   ```
   $ make uninstall
   ```

## Usage

By default, you must specify a kubectl command after "kubectl confirmation".
For example:
```
$ kubectl confirmation get pod -n kube-system
```

By setting an alias in your shell as shown below, you can use it just like the regular kubectl.

```
alias kubectl="kubectl confirmation"
```

## Configuration

### UNSAFE_RESOURCE_KINDS
UNSAFE_RESOURCE_KINDS is an environment variable that can point to custom resources requiring user authorization for kubectl apply execution.

Custom resources are described in the following format using a combination of kind, spec, and specValue: **kind{spec=specValue}**

- Custom Resource Example 1:
   ```
   $ cat NodeScalingRequest.yaml
   apiVersion: cluster.my.domain/v1alpha1
   kind: NodeScalingRequest
   metadata:
     name: my-delete-node
     namespace: default
   spec:
     nodeRequestType: delete
   ```
   &rarr; **NodeScalingRequest{nodeRequestType=delete}**

- Custom Resource Example 2: 
   ```
   $ cat CardScalingRequest.yaml
   apiVersion: cluster.my.domain/v1alpha1
   kind: CardScalingRequest
   metadata:
     name: my-deleting-card-1
     namespace: default
   spec:
     nodeName: my-node
     scalingParameter:
         op: delete
   ```
   &rarr; **CardScalingRequest{scalingParameter.op=delete}**

Environment variables can be specified as either CSV or files.

- Example for CSV in an environment variable.
   ```
   $ export UNSAFE_RESOURCE_KINDS="NodeScalingRequest{nodeRequestType=delete},CardScalingRequest{scalingParameter.op=delete}"
   ```

- Example for File in an environment variable.
   ```
   $ cat $HOME/unsafe-resources.txt
   NodeScalingRequest{nodeRequestType=delete}
   CardScalingRequest{scalingParameter.op=delete}
   $ export UNSAFE_RESOURCE_KINDS="$HOME/unsafe-resources.txt"
   ```

- Example of executing a custom resource apply
   ```
   $ kubectl confirmation apply -f NodeScalingRequest.yaml
   You are running a apply against current-context kubernetes-admin@kubernetes, continue? [yY] n
   I0106 10:29:18.054918 1546652 root.go:49] Not running command.

   $ kubectl confirmation apply -f NodeScalingRequest.yaml
   You are running a apply against current-context kubernetes-admin@kubernetes, continue? [yY] y
   nodescalingrequest.cluster.my.domain/my-delete-node created
   ```
   ```
   $ kubectl confirmation apply -f CardScalingRequest.yaml
   You are running a apply against current-context kubernetes-admin@kubernetes, continue? [yY] n
   I0106 11:25:55.279288 1570197 root.go:49] Not running command.

   $ kubectl confirmation apply -f CardScalingRequest.yaml
   You are running a apply against current-context kubernetes-admin@kubernetes, continue? [yY] y
   cardscalingrequest.cluster.my.domain/my-deleting-card-1 created
   ```

### UNSAFE_KUBECTL_COMMANDS
UNSAFE_KUBECTL_COMMANDS is an environment variable that can point to verbs requiring user authorization for kubectl execution.

Environment variables can be specified as either CSV or files.

- Example for CSV in an environment variable.
   ```
   $ export UNSAFE_KUBECTL_COMMANDS="version,get,delete"
   ```

- Example for File in an environment variable.
   ```
   $ cat $HOME/unsafe-kubectl-verbs.txt
   version
   get
   delete
   $ export UNSAFE_KUBECTL_COMMANDS="$HOME/unsafe-kubectl-verbs.txt"
   ```

- Example of Execution
   ```
   $ kubectl confirmation version
   You are running a version against current-context kubernetes-admin@kubernetes, continue? [yY] n
   I0105 17:46:30.981561 1170918 root.go:49] Not running command.

   $ kubectl confirmation version
   You are running a version against current-context kubernetes-admin@kubernetes, continue? [yY] y
   Client Version: v1.34.2
   Kustomize Version: v5.7.1
   Server Version: v1.34.2
   ```
   ```
   $ kubectl confirmation get pod -n kube-system
   You are running a get against current-context kubernetes-admin@kubernetes, continue? [yY] n
   I0105 17:52:11.129551 1173709 root.go:49] Not running command.

   $ kubectl confirmation get pod -n kube-system
   You are running a get against current-context kubernetes-admin@kubernetes, continue? [yY] y
   NAME                                       READY   STATUS    RESTARTS       AGE
   calico-kube-controllers-5c676f698c-hfsxr   1/1     Running   7              12d
   calico-node-gqx2t                          1/1     Running   7              12d
   calico-node-qjzh7                          1/1     Running   11             12d
   coredns-66bc5c9577-9hplg                   1/1     Running   7              12d
   etcd-wbcont                                1/1     Running   14             12d
   kube-apiserver-wbcont                      1/1     Running   11             12d
   kube-controller-manager-wbcont             1/1     Running   13             12d
   kube-proxy-kwfkz                           1/1     Running   13             12d
   kube-proxy-p2xc4                           1/1     Running   7              12d
   kube-scheduler-wbcont                      1/1     Running   10             12d
   ```
   ```
   $ kubectl confirmation delete -f NodeScalingRequest.yaml
   You are running a delete against current-context kubernetes-admin@kubernetes, continue? [yY] n
   I0106 10:30:20.991458 1547211 root.go:49] Not running command.

   $ kubectl confirmation delete -f NodeScalingRequest.yaml
   You are running a delete against current-context kubernetes-admin@kubernetes, continue? [yY] y
   nodescalingrequest.cluster.my.domain "my-delete-node" deleted from default namespace
   ```
   ```
   $ kubectl confirmation delete -f CardScalingRequest.yaml
   You are running a delete against current-context kubernetes-admin@kubernetes, continue? [yY] n
   I0106 11:26:35.181606 1570578 root.go:49] Not running command.

   $ kubectl confirmation delete -f CardScalingRequest.yaml
   You are running a delete against current-context kubernetes-admin@kubernetes, continue? [yY] y
   cardscalingrequest.cluster.my.domain "my-deleting-card-1" deleted from default namespace
   ```

