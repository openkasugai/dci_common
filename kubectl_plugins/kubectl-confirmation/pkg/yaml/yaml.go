// Copyright 2026 NTT, Inc.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package yaml

import (
	"io/ioutil"

	"gopkg.in/yaml.v3"
)

func ReadYamlToMap(yamlFilePath string) (map[string]interface{}, error) {
	data, err := ioutil.ReadFile(yamlFilePath)
	if err != nil {
		return nil, err
	}

	var yamlMap map[string]interface{}
	err = yaml.Unmarshal(data, &yamlMap)
	if err != nil {
		return nil, err
	}

	return yamlMap, nil
}

func GetStringFromYaml(m map[string]interface{}, keys []string) (string, bool) {
	var current interface{} = m

	// Get nested values
	for i, key := range keys {
		if i == len(keys)-1 {
			// Final key
			if currentMap, ok := current.(map[string]interface{}); ok {
				if val, ok := currentMap[key].(string); ok {
					return val, true
				}
			}
			return "", false
		}

		// Intermediate key
		if currentMap, ok := current.(map[string]interface{}); ok {
			current = currentMap[key]
		} else {
			return "", false
		}
	}
	return "", false
}
