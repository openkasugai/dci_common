package safety

import (
	"bufio"
	"errors"
	"fmt"
	"io/fs"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"strings"

	"k8s.io/klog/v2"

	"kubectl-confirmation/pkg/yaml"
)

func CheckSafe(kubectlVerb string, args []string) (bool, error) {
	isDryRun := checkDryRun(args)

	// First, verify whether the verb is `apply`.
	isVerbSafe, err := checkKubectlApply(args)
	if err != nil {
		return false, err
	}
	if isVerbSafe {
		// Second check if the verb is configured as unsafe
		isSafe, err := checkKubectlVerb(kubectlVerb)
		if err != nil {
			return false, err
		}
		isVerbSafe = isSafe
	}
	isSafe := isDryRun || isVerbSafe

	return isSafe, nil
}

func checkDryRun(cmds []string) bool {
	for _, i := range cmds {
		if strings.Contains(i, "--dry-run") {
			return true
		}
	}
	return false
}

func checkKubectlApply(cmds []string) (bool, error) {
	// When executing `kubectl apply`, check whether the Kind and Spec values of the resource
	// being applied are set to unsafe.
	if strings.Contains(cmds[0], "apply") {
		unsafeResources, err := getUnsafeResources()
		if err != nil {
			return false, err
		}
		if len(unsafeResources.resource) > 0 {
			yamlFiles, err := parseApply(cmds)
			if err != nil {
				return false, err
			}
			// read yaml
			for _, yamlFile := range yamlFiles {
				isUnsafeResource, err := unsafeResourceContains(unsafeResources, yamlFile)
				if err != nil {
					return false, err
				}
				if isUnsafeResource {
					return false, nil
				}
			}
		}
	}
	return true, nil
}

func parseApply(args []string) ([]string, error) {
	var files []string
	var dirs []string
	isR := false

	for i := 0; i < len(args); i++ {
		// Check filename flags
		if args[i] == "-f" && i+1 < len(args) {
			path := args[i+1]
			// url
			u, err := url.Parse(path)
			if err != nil {
				return nil, err
			}
			if u.Scheme != "" && u.Host != "" {
				i++
				continue
			}
			// stdin
			if path == "-" {
				i++
				continue
			}
			// directory or file
			info, err := os.Stat(path)
			if err != nil {
				return nil, err
			}
			if info.IsDir() {
				dirs = append(dirs, path)
			} else {
				files = append(files, path)
			}
			i++
		} else if before, after, found := strings.Cut(args[i], "="); found && before == "--filename" {
			path := after
			// url
			u, err := url.Parse(path)
			if err != nil {
				return nil, err
			}
			if u.Scheme != "" && u.Host != "" {
				continue
			}
			// stdin
			if path == "-" {
				continue
			}
			// directory or file
			info, err := os.Stat(path)
			if err != nil {
				return nil, err
			}
			if info.IsDir() {
				dirs = append(dirs, path)
			} else {
				files = append(files, path)
			}
		}

		// Check recursive flags
		if args[i] == "-R" || args[i] == "--recursive" {
			isR = true
		}
	}

	for _, dirPath := range dirs {
		if isR {
			// -R present: Treat as a directory and recursively retrieve .yaml and .yml files
			err := filepath.Walk(dirPath, func(path string, info os.FileInfo, err error) error {
				if err != nil {
					return err
				}
				if !info.IsDir() {
					extend := filepath.Ext(path)
					if extend == ".yaml" || extend == ".yml" {
						files = append(files, path)
					}
				}
				return nil
			})
			if err != nil {
				return nil, err
			}
		} else {
			// -R is absent: Treat as a directory and retrieve .yaml and .yml files.
			entries, err := os.ReadDir(dirPath)
			if err != nil {
				return nil, err
			}
			for _, entry := range entries {
				if !entry.IsDir() {
					extend := filepath.Ext(entry.Name())
					if extend == ".yaml" || extend == ".yml" {
						files = append(files, filepath.Join(dirPath, entry.Name()))
					}
				}
			}
		}
	}

	return files, nil
}

func checkKubectlVerb(kubectlVerb string) (bool, error) {
	// When the kubectl verb is omitted, only the help is displayed, so it is treated as safe.
	if kubectlVerb == "" {
		return true, nil
	}

	// check if the verb is configured as unsafe
	unsafeVerbs, err := getUnSafeVerbs()
	if err != nil {
		return false, err
	}
	if len(unsafeVerbs.verb) > 0 {
		return !unsafeVerbs.Contains(kubectlVerb), nil
	}

	return true, nil
}

func getUnsafeResources() (*Resources, error) {
	resources, err := parseResources(UnsafeResourceKinds)
	if err != nil {
		return nil, err
	}
	return resources, nil
}

func getUnSafeVerbs() (*Verbs, error) {
	verbs, err := parseVerbs(UnsafeKubectlCommands)
	if err != nil {
		return nil, err
	}
	return verbs, nil
}

func parseResources(env string) (*Resources, error) {
	var (
		resources *Resources = nil
		retErr    error      = nil
	)
	envVar := os.Getenv(env)
	if envVar == "" {
		// When the environment variable is empty
		resources, retErr = &EmptyResources, nil
	} else {
		if _, err := os.Stat(envVar); errors.Is(err, fs.ErrNotExist) {
			// When a CSV string is specified in an environment variable.
			sv := strings.Split(envVar, ",")
			if len(sv) >= 1 {
				resources, retErr = getResourcesFromSlice(sv)
			} else {
				retErr = fmt.Errorf("\"%s\" was provided by environment variable \"%s\", but its neither a word or existing file", envVar, env)
			}
		} else {
			// When a file path is specified in an environment variable
			resources, retErr = getResourcesFromFile(envVar)
		}
	}
	return resources, retErr
}

func getResourcesFromSlice(kubeResources []string) (*Resources, error) {
	resources := newResources()
	klog.V(3).Infof("Reading resource from environment variable.\n")
	for i := range kubeResources {
		if kubeResources[i] != "" {
			kind, spec, specValue, err := patternMatchResources(kubeResources[i])
			if err != nil {
				klog.Errorf("Failed to get resource from environment variable: %v", err)
				return nil, err
			}
			klog.V(3).Infof("Resources kind=%s, spec=%s, specValue=%s\n", kind, spec, specValue)
			resources.Add(kind, spec, specValue)
		}
	}
	return &resources, nil
}

func getResourcesFromFile(kubeResources string) (*Resources, error) {
	resources := newResources()
	file, err := os.Open(kubeResources)
	if err != nil {
		return nil, err
	}
	defer func(file *os.File) {
		err = file.Close()
		if err != nil {
			klog.Errorf("Failed to close file %s: %v", file.Name(), err)
		}
	}(file)

	klog.V(3).Infof("Reading resource from file %s.\n", kubeResources)
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		token := scanner.Text()
		if token != "" {
			klog.V(3).Infof("Adding resource \"%s\" to the unsafe list.\n", token)
			kind, spec, specValue, err := patternMatchResources(token)
			if err != nil {
				klog.Errorf("Failed to get resource from file %s: %v", file.Name(), err)
				return nil, err
			}
			klog.V(3).Infof("Resources kind=%s, spec=%s, specValue=%s\n", kind, spec, specValue)
			resources.Add(kind, spec, specValue)
		}
	}

	if err = scanner.Err(); err != nil {
		return nil, err
	}
	return &resources, nil
}

func patternMatchResources(line string) (string, string, string, error) {
	// Pattern match "kind{spec=specValue}"
	re := regexp.MustCompile(`^(\w+)\{(\w[\w.]*)=(\w+)\}$`)
	matches := re.FindStringSubmatch(line)
	if len(matches) != 4 {
		msg := "Does not match the pattern \"kind{spec=specValue}\""
		return "", "", "", errors.New(msg)
	}
	kind, spec, specValue := matches[1], matches[2], matches[3]
	return kind, spec, specValue, nil
}

func newResources() Resources {
	return Resources{resource: make(map[string]map[string]map[string]Void)}
}

func parseVerbs(env string) (*Verbs, error) {
	var (
		verbs  *Verbs = nil
		retErr error  = nil
	)
	envVar := os.Getenv(env)
	if envVar == "" {
		// When the environment variable is empty
		verbs, retErr = &EmptyVerbs, nil
	} else {
		if _, err := os.Stat(envVar); errors.Is(err, fs.ErrNotExist) {
			// When a CSV string is specified in an environment variable.
			sv := strings.Split(envVar, ",")
			if len(sv) >= 1 {
				verbs, retErr = getVerbsFromSlice(sv)
			} else {
				retErr = fmt.Errorf("\"%s\" was provided by environment variable \"%s\", but its neither a word or existing file", envVar, env)
			}
		} else {
			// When a file path is specified in an environment variable
			verbs, retErr = getVerbsFromFile(envVar)
		}
	}
	return verbs, retErr
}

func getVerbsFromSlice(kubectlVerbs []string) (*Verbs, error) {
	verbs := newVerbs()
	for i := range kubectlVerbs {
		if kubectlVerbs[i] != "" {
			verbs.Add(kubectlVerbs[i])
		}
	}
	return &verbs, nil
}

func getVerbsFromFile(kubectlVerbs string) (*Verbs, error) {
	verbs := newVerbs()
	file, err := os.Open(kubectlVerbs)
	if err != nil {
		return nil, err
	}
	defer func(file *os.File) {
		err = file.Close()
		if err != nil {
			klog.Errorf("Failed to close file %s: %v", file.Name(), err)
		}
	}(file)

	klog.V(3).Infof("Reading kubectl verbs from file %s.\n", kubectlVerbs)
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		token := scanner.Text()
		if token != "" {
			klog.V(3).Infof("Adding kubectl verb \"%s\" to the safe list.\n", token)
			verbs.Add(token)
		}
	}

	if err = scanner.Err(); err != nil {
		return nil, err
	}
	return &verbs, nil
}

func newVerbs() Verbs {
	return Verbs{verb: make(map[string]Void)}
}

func unsafeResourceContains(unsafeResources *Resources, yamlFilePath string) (bool, error) {
	// Read YAML file to get resources
	yamlResources, err := yaml.ReadYamlToMap(yamlFilePath)
	if err != nil {
		return false, err
	}

	// Get the "kind" item from YAML
	yamlKind, isExist := yaml.GetStringFromYaml(yamlResources, []string{"kind"})
	if !isExist {
		return false, nil
	}

	for unSafeKind := range unsafeResources.resource {
		// Comparing YAML "kind" item and Unsafe lists
		if unSafeKind != yamlKind {
			continue
		}
		for unSafeSpec := range unsafeResources.resource[unSafeKind] {
			// Comparing YAML "spec" item and Unsafe lists
			sv := strings.Split(unSafeSpec, ".")
			unSafeSpecSlice := []string{"spec"}
			for _, s := range sv {
				unSafeSpecSlice = append(unSafeSpecSlice, s)
			}
			yamlSpecValue, isExist := yaml.GetStringFromYaml(yamlResources, unSafeSpecSlice)
			if !isExist {
				continue
			}
			for unSafeSpecValue := range unsafeResources.resource[unSafeKind][unSafeSpec] {
				if unSafeSpecValue != yamlSpecValue {
					continue
				}
				return true, nil
			}
		}
	}
	return false, nil
}
