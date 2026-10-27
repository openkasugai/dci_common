#!/bin/bash -x

kubectl get cluster -A -o wide
kubectl get kubeadmconfigtemplates.bootstrap.cluster.x-k8s.io -A -o wide
kubectl get kubeadmconfig -A -o wide
kubectl get kubeadmcontrolplane -A -o wide
kubectl get machinedeployment -A -o wide
kubectl get machine -A -o wide
kubectl get dciclusters.infrastructure.cluster.x-k8s.io -A
kubectl get dcimachinetemplates.infrastructure.cluster.x-k8s.io -A
kubectl get dcimachines.infrastructure.cluster.x-k8s.io -A
kubectl get logicalservers.example.com -A -o wide
kubectl get tenantlogicalinfras.example.com -A  -o wide

kubectl get cluster -A --no-headers | while read ns name rest; do
  echo "===== ${ns}/${name} ====="
  clusterctl describe cluster -n "${ns}" "${name}"
done
