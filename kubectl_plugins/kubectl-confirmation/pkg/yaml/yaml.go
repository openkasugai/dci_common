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
