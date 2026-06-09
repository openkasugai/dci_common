#!/bin/bash -x

LOG_DIR=./logs

# Flag to switch the target cluster to access
# If TENANT_NAMESPACE is set, access the corresponding tenant cluster using ($CONFIG_DIR$TENANT_NAMESPACE.kubeconfig)
# If TENANT_NAMESPACE is empty, access the default cluster on this server (environment variable KUBECONFIG)
TENANT_NAMESPACE=tenant-1
# TENANT_NAMESPACE=""

CONFIG_DIR=$HOME/tenant-for-
if [ -z "$TENANT_NAMESPACE" ]; then
    KUBECONFIG_TENANT=""
else
    KUBECONFIG_TENANT="--kubeconfig=$CONFIG_DIR$TENANT_NAMESPACE.kubeconfig"
fi

if [ -d $LOG_DIR ];then
    rm -f $LOG_DIR/*
else
    mkdir $LOG_DIR
fi

mkdir $LOG_DIR/dciapp-nixlcomm
mkdir $LOG_DIR/dciapp-nixlcomm/describe
mkdir $LOG_DIR/dciapp-nixlcomm/app-conn-control-info-manager-dci
mkdir $LOG_DIR/dciapp-nixlcomm/vector
mkdir $LOG_DIR/json
mkdir $LOG_DIR/dciappconnection
mkdir $LOG_DIR/connectendpoint
mkdir $LOG_DIR/dciappstate
mkdir $LOG_DIR/argo-events
mkdir $LOG_DIR/temporal
mkdir $LOG_DIR/infra-resources
mkdir $LOG_DIR/infra-resources/resourceclaim
mkdir $LOG_DIR/infra-resources/resourceclaimtemplates
mkdir $LOG_DIR/prometheus-adapter
mkdir $LOG_DIR/hpa

# App logs
kubectl $KUBECONFIG_TENANT get pod -A |grep -v NAME |grep dciapp- | awk -v kubeconfig="$KUBECONFIG_TENANT" -v logdir="$LOG_DIR/dciapp-nixlcomm" '{print "kubectl " kubeconfig " logs "$2" -n "$1" > " logdir "/"$2".log"}' | bash
kubectl $KUBECONFIG_TENANT get pod -A |grep -v NAME |grep dciapp-nixlcomm-conn- | awk -v kubeconfig="$KUBECONFIG_TENANT" -v logdir="$LOG_DIR/dciapp-nixlcomm/app-conn-control-info-manager-dci" '{print "kubectl " kubeconfig " logs "$2" -n "$1" -c app-conn-control-info-manager-dci > " logdir "/"$2"-app-conn-control-info-manager-dci.log"}' | bash
kubectl $KUBECONFIG_TENANT get pod -A |grep -v NAME |grep dciapp-nixlcomm- | awk -v kubeconfig="$KUBECONFIG_TENANT" -v logdir="$LOG_DIR/dciapp-nixlcomm/vector" '{print "kubectl " kubeconfig " logs "$2" -n "$1" -c vector > " logdir "/"$2"-vector.log"}' | bash
# Describe App
kubectl $KUBECONFIG_TENANT get pod -A |grep -v NAME |grep dciapp-nixlcomm- | awk -v kubeconfig="$KUBECONFIG_TENANT" -v logdir="$LOG_DIR/dciapp-nixlcomm/describe" '{print "kubectl " kubeconfig " describe pod -n "$1" "$2" > " logdir "/"$2".log"}' | bash

# AppConnInfoMaker logs
kubectl $KUBECONFIG_TENANT get pod -A |grep -v NAME |grep app-conn-info-maker-dci-controller-manager | awk -v kubeconfig="$KUBECONFIG_TENANT" -v logdir="$LOG_DIR" '{print "kubectl " kubeconfig " logs "$2" -n "$1" > " logdir "/"$2".log"}' | bash

# Temporal logs
kubectl $KUBECONFIG_TENANT get pod -A |grep -v NAME |grep temporal-workflow | awk -v kubeconfig="$KUBECONFIG_TENANT" -v logdir="$LOG_DIR/temporal" '{print "kubectl " kubeconfig " logs "$2" -n "$1" > " logdir "/"$2".log"}' | bash
kubectl $KUBECONFIG_TENANT get pod -A |grep -v NAME |grep temporal-gateway | awk -v kubeconfig="$KUBECONFIG_TENANT" -v logdir="$LOG_DIR/temporal" '{print "kubectl " kubeconfig " logs "$2" -n "$1" > " logdir "/"$2".log"}' | bash
kubectl $KUBECONFIG_TENANT get pod -A |grep -v NAME |grep temporal-client | awk -v kubeconfig="$KUBECONFIG_TENANT" -v logdir="$LOG_DIR/temporal" '{print "kubectl " kubeconfig " logs "$2" -n "$1" > " logdir "/"$2".log"}' | bash

# Argo Events logs
kubectl $KUBECONFIG_TENANT get pod -A |grep -v NAME |grep argo-events | awk -v kubeconfig="$KUBECONFIG_TENANT" -v logdir="$LOG_DIR/argo-events" '{print "kubectl " kubeconfig " logs "$2" -n "$1" > " logdir "/"$2".log"}' | bash

# Json files
kubectl $KUBECONFIG_TENANT get pod -A |grep -v NAME |grep dciapp-nixlcomm-conn | awk -v kubeconfig="$KUBECONFIG_TENANT" -v logdir="$LOG_DIR/json" '{print "kubectl " kubeconfig " exec -n "$1" "$2" -- cat /app-conn-control-info-manager-dci/appConnectControlInfo.json > " logdir "/"$2".json"}'| bash

# DCIAppConnection yaml files
kubectl $KUBECONFIG_TENANT get dciappconnection -A |grep -v NAME |grep dciapp | awk -v kubeconfig="$KUBECONFIG_TENANT" -v logdir="$LOG_DIR/dciappconnection" '{print "kubectl " kubeconfig " get dciappconnection "$2" -n "$1" -o yaml > " logdir "/"$2".yaml"}' | bash

# ConnectEndpoint yaml files
kubectl $KUBECONFIG_TENANT get connectendpoint -A |grep -v NAME |grep dciapp | awk -v kubeconfig="$KUBECONFIG_TENANT" -v logdir="$LOG_DIR/connectendpoint" '{print "kubectl " kubeconfig " get connectendpoint "$2" -n "$1" -o yaml > " logdir "/"$2".yaml"}' | bash

# DCIAppState yaml files
kubectl $KUBECONFIG_TENANT get dciappstate -A |grep -v NAME |grep dciapp | awk -v kubeconfig="$KUBECONFIG_TENANT" -v logdir="$LOG_DIR/dciappstate" '{print "kubectl " kubeconfig " get dciappstate "$2" -n "$1" -o yaml > " logdir "/"$2".yaml"}' | bash


kubectl $KUBECONFIG_TENANT get service,endpointslice -n dci > $LOG_DIR/get_service-AND-endpointslice.txt

# Describe infra-resources
kubectl $KUBECONFIG_TENANT describe hostdevicenetwork > $LOG_DIR/infra-resources/hostdevicenetwork.log
kubectl $KUBECONFIG_TENANT describe ippool.nv-ipam.nvidia.com ippool-demo -n nvidia-network-operator > $LOG_DIR/infra-resources/ippool-demo.log
kubectl $KUBECONFIG_TENANT get resourceclaim -A |grep -v NAME | awk -v kubeconfig="$KUBECONFIG_TENANT" -v logdir="$LOG_DIR/infra-resources/resourceclaim" '{print "kubectl " kubeconfig " describe resourceclaim -n "$1" "$2" > " logdir "/"$2".log"}' | bash
kubectl $KUBECONFIG_TENANT get resourceclaimtemplates.resource.k8s.io -A |grep -v NAME | awk -v kubeconfig="$KUBECONFIG_TENANT" -v logdir="$LOG_DIR/infra-resources/resourceclaimtemplates" '{print "kubectl " kubeconfig " describe resourceclaimtemplate -n "$1" "$2" > " logdir "/"$2".log"}' | bash

# Prometheus Adapter logs
kubectl $KUBECONFIG_TENANT get pod -A |grep -v NAME |grep prometheus-adapter- | awk -v kubeconfig="$KUBECONFIG_TENANT" -v logdir="$LOG_DIR/prometheus-adapter" '{print "kubectl " kubeconfig " logs "$2" -n "$1" > " logdir "/"$2".log"}' | bash

# HPA describe
kubectl $KUBECONFIG_TENANT get hpa -A |grep -v NAME |grep dciapp-nixlcomm- | awk -v kubeconfig="$KUBECONFIG_TENANT" -v logdir="$LOG_DIR/hpa" '{print "kubectl " kubeconfig " describe hpa -n "$1" "$2" > " logdir "/"$2".log"}' | bash

# Get deployment, replicaset and pod yaml files
LOG_DIR_ConnProc=$LOG_DIR/connproc
mkdir $LOG_DIR_ConnProc
mkdir $LOG_DIR_ConnProc/deployment
mkdir $LOG_DIR_ConnProc/replicaset
mkdir $LOG_DIR_ConnProc/pod

kubectl $KUBECONFIG_TENANT get deployment -A |grep -v NAME |grep dciapp- | awk -v kubeconfig="$KUBECONFIG_TENANT" -v logdir="$LOG_DIR_ConnProc/deployment" '{print "kubectl " kubeconfig " get deployment "$2" -n "$1" -o yaml > " logdir "/"$2".yaml"}' | bash
kubectl $KUBECONFIG_TENANT get deployment -A |grep -v NAME |grep app-conn-info-maker- | awk -v kubeconfig="$KUBECONFIG_TENANT" -v logdir="$LOG_DIR_ConnProc/deployment" '{print "kubectl " kubeconfig " get deployment "$2" -n "$1" -o yaml > " logdir "/"$2".yaml"}' | bash
kubectl $KUBECONFIG_TENANT get deployment -A |grep -v NAME |grep prometheus-adapter | awk -v kubeconfig="$KUBECONFIG_TENANT" -v logdir="$LOG_DIR_ConnProc/deployment" '{print "kubectl " kubeconfig " get deployment "$2" -n "$1" -o yaml > " logdir "/"$2".yaml"}' | bash

kubectl $KUBECONFIG_TENANT get replicaset -A |grep -v NAME |grep dciapp- | awk -v kubeconfig="$KUBECONFIG_TENANT" -v logdir="$LOG_DIR_ConnProc/replicaset" '{print "kubectl " kubeconfig " get replicaset "$2" -n "$1" -o yaml > " logdir "/"$2".yaml"}' | bash
kubectl $KUBECONFIG_TENANT get replicaset -A |grep -v NAME |grep app-conn-info-maker- | awk -v kubeconfig="$KUBECONFIG_TENANT" -v logdir="$LOG_DIR_ConnProc/replicaset" '{print "kubectl " kubeconfig " get replicaset "$2" -n "$1" -o yaml > " logdir "/"$2".yaml"}' | bash
kubectl $KUBECONFIG_TENANT get replicaset -A |grep -v NAME |grep prometheus-adapter | awk -v kubeconfig="$KUBECONFIG_TENANT" -v logdir="$LOG_DIR_ConnProc/replicaset" '{print "kubectl " kubeconfig " get replicaset "$2" -n "$1" -o yaml > " logdir "/"$2".yaml"}' | bash

kubectl $KUBECONFIG_TENANT get pod -A |grep -v NAME |grep dciapp- | awk -v kubeconfig="$KUBECONFIG_TENANT" -v logdir="$LOG_DIR_ConnProc/pod" '{print "kubectl " kubeconfig " get pod "$2" -n "$1" -o yaml > " logdir "/"$2".yaml"}' | bash
kubectl $KUBECONFIG_TENANT get pod -A |grep -v NAME |grep app-conn-info-maker- | awk -v kubeconfig="$KUBECONFIG_TENANT" -v logdir="$LOG_DIR_ConnProc/pod" '{print "kubectl " kubeconfig " get pod "$2" -n "$1" -o yaml > " logdir "/"$2".yaml"}' | bash
kubectl $KUBECONFIG_TENANT get pod -A |grep -v NAME |grep prometheus-adapter | awk -v kubeconfig="$KUBECONFIG_TENANT" -v logdir="$LOG_DIR_ConnProc/pod" '{print "kubectl " kubeconfig " get pod "$2" -n "$1" -o yaml > " logdir "/"$2".yaml"}' | bash
