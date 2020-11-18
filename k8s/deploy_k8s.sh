#!/bin/bash

# 2 vCPU, 8 GB RAM, $0.075462/hour
#MACHINETYPE="e2-standard-2"

# 4	vCPU, 16 GB RAM, $0.134012/hour
MACHINETYPE="e2-standard-4"
NAME="${USER}-geo-tourist"
ZONE="us-east4-b"

# 1. Create the GKE K8s cluster
gcloud container clusters create $NAME --zone=$ZONE --machine-type=$MACHINETYPE --num-nodes=5

ACCOUNT=$( gcloud info | perl -ne 'print "$1\n" if /^Account: \[([^@]+@[^\]]+)\]$/' )

kubectl create clusterrolebinding cluster-admin-binding --clusterrole=cluster-admin --user=$ACCOUNT

# 2. Create the CockroachDB cluster
YAML="https://raw.githubusercontent.com/cockroachdb/cockroach/master/cloud/kubernetes/cockroachdb-statefulset.yaml"
kubectl apply -f $YAML

# 3. Initialize DB / cluster
YAML="https://raw.githubusercontent.com/cockroachdb/cockroach/master/cloud/kubernetes/cluster-init.yaml"
kubectl apply -f $YAML

cat <<EoM

WAIT until the output from "kubectl get pods" shows a status of "Running" for
the three 'cockroachdb-N' nodes; e.g.

$ kubectl get pods
NAME                                READY   STATUS      RESTARTS   AGE
cluster-init-67frx                  0/1     Completed   0          8h
cockroachdb-0                       1/1     Running     0          8h
cockroachdb-1                       1/1     Running     0          8h
cockroachdb-2                       1/1     Running     0          8h

EoM

# 4. Create table, index, and load data
YAML="./data-loader.yaml"
kubectl apply -f $YAML

cat <<EoM

WAIT until "kubectl get pods" shows "Completed" for the loader process; e.g.

$ kubectl get pods
NAME                                READY   STATUS      RESTARTS   AGE
crdb-geo-loader                     0/1     Completed   0          7h2m

EoM

# 5. Start the Web UI
YAML="./crdb-geo-tourist.yaml"
kubectl apply -f $YAML

# FINALLY: tear it all down
YAML="./crdb-geo-tourist.yaml"
kubectl delete -f $YAML
YAML="./data-loader.yaml"
kubectl delete -f $YAML
YAML="https://raw.githubusercontent.com/cockroachdb/cockroach/master/cloud/kubernetes/cockroachdb-statefulset.yaml"
kubectl delete -f $YAML
YAML="https://raw.githubusercontent.com/cockroachdb/cockroach/master/cloud/kubernetes/cluster-init.yaml"
kubectl delete -f $YAML

gcloud container clusters delete $NAME --zone=$ZONE --quiet

