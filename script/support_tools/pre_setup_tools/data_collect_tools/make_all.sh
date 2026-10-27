#!/bin/bash

./maas_commission.sh
./maas_info.sh
./run_cdi.sh
./make_config_yaml.sh > tmp.yaml
(cat tmp.yaml; printf '\n'; cat cdi.yaml) > config.yaml
rm tmp.yaml cdi.yaml
