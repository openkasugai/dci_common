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

package safety

import (
	"os"
	"path/filepath"
	"reflect"
	"testing"
)

func Test_checkDryRun(t *testing.T) {
	type args struct {
		cmds []string
	}
	testCases := []struct {
		name   string
		args   args
		expect bool
	}{
		{name: "DryRun1", args: args{cmds: []string{"get", "pod", "foo", "--dry-run=client"}}, expect: true},
		{name: "DryRun2", args: args{cmds: []string{"get", "pod", "foo", "--dry-run=server"}}, expect: true},
		{name: "DryRun3", args: args{cmds: []string{"delete", "pod", "foo", "--dry-run=client"}}, expect: true},
		{name: "DryRun4", args: args{cmds: []string{"delete", "pod", "foo", "--dry-run=server"}}, expect: true},
		{name: "NotDryRun1", args: args{cmds: []string{"get", "pod", "foo"}}, expect: false},
		{name: "NotDryRun2", args: args{cmds: []string{"delete", "pod", "foo"}}, expect: false},
	}
	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			if result := checkDryRun(tc.args.cmds); result != tc.expect {
				t.Errorf("checkDryRun() = %v, Expected value is \"%v\"", result, tc.expect)
			}
		})
	}
}

func Test_getResourcesFromFile(t *testing.T) {
	type args struct {
		cmds string
	}
	testCases := []struct {
		name      string
		args      args
		expect    *Resources
		expectErr bool
	}{
		// NodeScalingRequest{nodeRequestType=delete}
		// -> "NodeScalingRequest": {"nodeRequestType": {"delete": Empty,},}
		// CardScalingRequest{scalingParameter.op=delete}
		// -> "CardScalingRequest": {"scalingParameter.op": {"delete": Empty,},}
		// CardScalingRequest{scalingParameter.op=replace}
		// -> "CardScalingRequest": {"scalingParameter.op": {"replace": Empty,},}
		{name: "FileExist", args: args{cmds: "./testdata/environment/unsafe-resources.txt"},
			expect: &Resources{resource: map[string]map[string]map[string]Void{
				"NodeScalingRequest": {
					"nodeRequestType": {
						"delete": Empty,
					},
				},
				"CardScalingRequest": {
					"scalingParameter.op": {
						"delete":  Empty,
						"replace": Empty,
					},
				},
			},
			}, expectErr: false},
		{name: "FileDoesntExist", args: args{cmds: "NodeScalingRequest{nodeRequestType=delete}"},
			expect: nil, expectErr: true},
	}
	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			result, err := getResourcesFromFile(tc.args.cmds)
			if (err != nil) != tc.expectErr {
				t.Errorf("getResourcesFromFile() result Err = %v, Expect Err is %v", err, tc.expectErr)
				return
			}
			if !reflect.DeepEqual(result, tc.expect) {
				t.Errorf("getResourcesFromFile() result value = %v, Expect value is %v", result, tc.expect)
			}
		})
	}
}

func Test_getVerbsFromFile(t *testing.T) {
	type args struct {
		cmds string
	}
	testCases := []struct {
		name      string
		args      args
		expect    *Verbs
		expectErr bool
	}{
		{name: "FileExist", args: args{cmds: "./testdata/environment/unsafe-kubectl-verbs.txt"},
			expect: &Verbs{verb: map[string]Void{"delete": Empty, "edit": Empty, "cordon": Empty}}, expectErr: false},
		{name: "FileDoesntExist", args: args{cmds: "delete"},
			expect: nil, expectErr: true},
	}
	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			result, err := getVerbsFromFile(tc.args.cmds)
			if (err != nil) != tc.expectErr {
				t.Errorf("getVerbsFromFile() result Err = %v, Expect Err is %v", err, tc.expectErr)
				return
			}
			if !reflect.DeepEqual(result, tc.expect) {
				t.Errorf("getVerbsFromFile() result value = %v, Expect value is %v", result, tc.expect)
			}
		})
	}
}

func Test_parseResources(t *testing.T) {
	testCases := []struct {
		name      string
		value     string
		expect    *Resources
		env       string
		expectErr bool
	}{
		{name: "EnvOneValue", value: "NodeScalingRequest{nodeRequestType=delete}",
			expect: &Resources{resource: map[string]map[string]map[string]Void{
				"NodeScalingRequest": {
					"nodeRequestType": {
						"delete": Empty,
					},
				},
			},
			}, expectErr: false, env: UnsafeResourceKinds},
		{name: "EnvManyValue1", value: "NodeScalingRequest{nodeRequestType=delete},CardScalingRequest{scalingParameter.op=delete},CardScalingRequest{scalingParameter.op=replace}",
			expect: &Resources{resource: map[string]map[string]map[string]Void{
				"NodeScalingRequest": {
					"nodeRequestType": {
						"delete": Empty,
					},
				},
				"CardScalingRequest": {
					"scalingParameter.op": {
						"delete":  Empty,
						"replace": Empty,
					},
				},
			},
			}, expectErr: false, env: UnsafeResourceKinds},
		{name: "EnvManyValue2", value: "NodeScalingRequest{nodeRequestType=delete},CardScalingRequest{scalingParameter.op=delete},CardScalingRequest{scalingParameter.op=replace}",
			expect: &Resources{resource: map[string]map[string]map[string]Void{
				"CardScalingRequest": {
					"scalingParameter.op": {
						"replace": Empty,
						"delete":  Empty,
					},
				},
				"NodeScalingRequest": {
					"nodeRequestType": {
						"delete": Empty,
					},
				},
			},
			}, expectErr: false, env: UnsafeResourceKinds},
		{name: "EnvNoValues", value: "", expect: &EmptyResources, expectErr: false, env: UnsafeResourceKinds},
		{name: "EnvInNoValues", value: "NodeScalingRequest{nodeRequestType=delete},,CardScalingRequest{scalingParameter.op=replace}",
			expect: &Resources{resource: map[string]map[string]map[string]Void{
				"NodeScalingRequest": {
					"nodeRequestType": {
						"delete": Empty,
					},
				},
				"CardScalingRequest": {
					"scalingParameter.op": {
						"replace": Empty,
					},
				},
			},
			}, expectErr: false, env: UnsafeResourceKinds},
		{name: "EnvEndInComma", value: "NodeScalingRequest{nodeRequestType=delete},",
			expect: &Resources{resource: map[string]map[string]map[string]Void{
				"NodeScalingRequest": {
					"nodeRequestType": {
						"delete": Empty,
					},
				},
			},
			}, expectErr: false, env: UnsafeResourceKinds},
		{name: "EnvInvalidValues", value: "dummy", expect: nil, expectErr: true, env: UnsafeResourceKinds},
		{name: "File1", value: getTestDataFile(t, "testdata/environment/unsafe-resources.txt"),
			expect: &Resources{resource: map[string]map[string]map[string]Void{
				"NodeScalingRequest": {
					"nodeRequestType": {
						"delete": Empty,
					},
				},
				"CardScalingRequest": {
					"scalingParameter.op": {
						"delete":  Empty,
						"replace": Empty,
					},
				},
			},
			}, expectErr: false, env: UnsafeResourceKinds},
		{name: "File2", value: getTestDataFile(t, "testdata/environment/unsafe-resources.txt"),
			expect: &Resources{resource: map[string]map[string]map[string]Void{
				"CardScalingRequest": {
					"scalingParameter.op": {
						"replace": Empty,
						"delete":  Empty,
					},
				},
				"NodeScalingRequest": {
					"nodeRequestType": {
						"delete": Empty,
					},
				},
			},
			}, expectErr: false, env: UnsafeResourceKinds},
		{name: "EmptyFile", value: getTestDataFile(t, "testdata/environment/empty.txt"),
			expect: &Resources{resource: map[string]map[string]map[string]Void{}}, expectErr: false, env: UnsafeResourceKinds},
		{name: "InvalidFile", value: getTestDataFile(t, "testdata/environment/unsafe-resources_invalid.txt"),
			expect: nil, expectErr: true, env: UnsafeResourceKinds},
	}
	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			t.Setenv(tc.env, tc.value)
			result, err := parseResources(tc.env)
			if (err != nil) != tc.expectErr {
				t.Errorf("parseResources() result Err = %v, Expect Err is %v", err, tc.expectErr)
				return
			}
			if !reflect.DeepEqual(result, tc.expect) {
				t.Errorf("parseResources() result value = %v, Expect value is %v", result, tc.expect)
			}
		})
	}
}

func Test_parseVerbs(t *testing.T) {
	testCases := []struct {
		name      string
		value     string
		expect    *Verbs
		env       string
		expectErr bool
	}{
		{name: "EnvOneValue", value: "delete", expect: &Verbs{verb: map[string]Void{"delete": Empty}}, expectErr: false, env: UnsafeKubectlCommands},
		{name: "EnvManyValues1", value: "delete,edit,cordon", expect: &Verbs{verb: map[string]Void{"delete": Empty, "edit": Empty, "cordon": Empty}}, expectErr: false, env: UnsafeKubectlCommands},
		{name: "EnvManyValues2", value: "delete,edit,cordon", expect: &Verbs{verb: map[string]Void{"cordon": Empty, "delete": Empty, "edit": Empty}}, expectErr: false, env: UnsafeKubectlCommands},
		{name: "EnvNoValues", value: "", expect: &EmptyVerbs, expectErr: false, env: UnsafeKubectlCommands},
		{name: "EnvInNoValues", value: "delete,,cordon", expect: &Verbs{verb: map[string]Void{"delete": Empty, "cordon": Empty}}, expectErr: false, env: UnsafeKubectlCommands},
		{name: "EnvEndInComma", value: "delete,", expect: &Verbs{verb: map[string]Void{"delete": Empty}}, expectErr: false, env: UnsafeKubectlCommands},
		{name: "File1", value: getTestDataFile(t, "testdata/environment/unsafe-kubectl-verbs.txt"), expect: &Verbs{verb: map[string]Void{"delete": Empty, "edit": Empty, "cordon": Empty}}, expectErr: false, env: UnsafeKubectlCommands},
		{name: "File2", value: getTestDataFile(t, "testdata/environment/unsafe-kubectl-verbs.txt"), expect: &Verbs{verb: map[string]Void{"cordon": Empty, "delete": Empty, "edit": Empty}}, expectErr: false, env: UnsafeKubectlCommands},
		{name: "EmptyFile", value: getTestDataFile(t, "testdata/environment/empty.txt"), expect: &Verbs{verb: map[string]Void{}}, expectErr: false, env: UnsafeKubectlCommands},
	}
	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			t.Setenv(tc.env, tc.value)
			result, err := parseVerbs(tc.env)
			if (err != nil) != tc.expectErr {
				t.Errorf("parseVerbs() result Err = %v, Expect Err is %v", err, tc.expectErr)
				return
			}
			if !reflect.DeepEqual(result, tc.expect) {
				t.Errorf("parseVerbs() result value = %v, Expect value is %v", result, tc.expect)
			}
		})
	}
}

func getTestDataFile(t *testing.T, file string) string {
	absFilePath, err := filepath.Abs(file)
	if err != nil {
		t.Errorf("Error: %v", err)
	}
	if _, err := os.Stat(absFilePath); err != nil {
		t.Errorf("Error: %v", err)
	}
	return absFilePath
}

func Test_unsafeResourceContains(t *testing.T) {
	type args struct {
		value *Resources
		yaml  string
	}
	testCases := []struct {
		name      string
		args      args
		expect    bool
		expectErr bool
	}{
		{name: "YamlUnsafeKindSpec1", args: args{
			value: &Resources{resource: map[string]map[string]map[string]Void{
				"NodeScalingRequest": {
					"nodeRequestType": {
						"delete": Empty,
					},
				},
				"CardScalingRequest": {
					"scalingParameter.op": {
						"delete":  Empty,
						"replace": Empty,
					},
				},
			}},
			yaml: "testdata/yaml/cr/nsr/NodeScalingRequest-delete.yaml",
		}, expect: true, expectErr: false},
		{name: "YamlUnsafeKindSpec2", args: args{
			value: &Resources{resource: map[string]map[string]map[string]Void{
				"NodeScalingRequest": {
					"nodeRequestType": {
						"delete": Empty,
					},
				},
				"CardScalingRequest": {
					"scalingParameter.op": {
						"delete":  Empty,
						"replace": Empty,
					},
				},
			}},
			yaml: "testdata/yaml/cr/csr/CardScalingRequest-delete.yaml",
		}, expect: true, expectErr: false},
		{name: "YamlUnsafeKindSpec3", args: args{
			value: &Resources{resource: map[string]map[string]map[string]Void{
				"NodeScalingRequest": {
					"nodeRequestType": {
						"delete": Empty,
					},
				},
				"CardScalingRequest": {
					"scalingParameter.op": {
						"delete":  Empty,
						"replace": Empty,
					},
				},
			}},
			yaml: "testdata/yaml/cr/csr/CardScalingRequest-replace.yaml",
		}, expect: true, expectErr: false},
		{name: "YamlSafeKind", args: args{
			value: &Resources{resource: map[string]map[string]map[string]Void{
				"NodeScalingRequest": {
					"nodeRequestType": {
						"delete": Empty,
					},
				},
				"CardScalingRequest": {
					"scalingParameter.op": {
						"delete":  Empty,
						"replace": Empty,
					},
				},
			}},
			yaml: "testdata/yaml/cr/other/Other.yaml",
		}, expect: false, expectErr: false},
		{name: "YamlSafeSpec", args: args{
			value: &Resources{resource: map[string]map[string]map[string]Void{
				"NodeScalingRequest": {
					"nodeRequestType": {
						"delete": Empty,
					},
				},
				"CardScalingRequest": {
					"scalingParameter.op": {
						"delete":  Empty,
						"replace": Empty,
					},
				},
			}},
			yaml: "testdata/yaml/cr/nsr/NodeScalingRequest-spec_other.yaml",
		}, expect: false, expectErr: false},
		{name: "YamlSafeKindSpec1", args: args{
			value: &Resources{resource: map[string]map[string]map[string]Void{
				"NodeScalingRequest": {
					"nodeRequestType": {
						"delete": Empty,
					},
				},
				"CardScalingRequest": {
					"scalingParameter.op": {
						"delete":  Empty,
						"replace": Empty,
					},
				},
			}},
			yaml: "testdata/yaml/cr/nsr/NodeScalingRequest-create.yaml",
		}, expect: false, expectErr: false},
		{name: "YamlSafeKindSpec2", args: args{
			value: &Resources{resource: map[string]map[string]map[string]Void{
				"NodeScalingRequest": {
					"nodeRequestType": {
						"delete": Empty,
					},
				},
				"CardScalingRequest": {
					"scalingParameter.op": {
						"delete":  Empty,
						"replace": Empty,
					},
				},
			}},
			yaml: "testdata/yaml/cr/csr/CardScalingRequest-add.yaml",
		}, expect: false, expectErr: false},
		{name: "YamlDoesntExist", args: args{
			value: &Resources{resource: map[string]map[string]map[string]Void{
				"NodeScalingRequest": {
					"nodeRequestType": {
						"delete": Empty,
					},
				},
				"CardScalingRequest": {
					"scalingParameter.op": {
						"delete":  Empty,
						"replace": Empty,
					},
				},
			}},
			yaml: "",
		}, expect: false, expectErr: true},
	}
	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			result, err := unsafeResourceContains(tc.args.value, tc.args.yaml)
			if (err != nil) != tc.expectErr {
				t.Errorf("unsafeResourceContains() result error = %v, Expect Err is %v", err, tc.expectErr)
				return
			}
			if result != tc.expect {
				t.Errorf("unsafeResourceContains() result value = %v, Expect value is %v", result, tc.expect)
			}
		})
	}
}

func Test_checkKubectlVerb(t *testing.T) {
	type args struct {
		verb string
	}
	testCases := []struct {
		name      string
		args      args
		env       string
		envValue  string
		expect    bool
		expectErr bool
	}{
		{name: "EmptyVerb", args: args{verb: ""}, env: UnsafeKubectlCommands, envValue: "delete", expect: true, expectErr: false},
		{name: "DefaultSafeVerbTrue", args: args{verb: "get"}, env: UnsafeKubectlCommands, envValue: "delete", expect: true, expectErr: false},
		{name: "DefaultSafeVerbFalse", args: args{verb: "delete"}, env: UnsafeKubectlCommands, envValue: "delete", expect: false, expectErr: false},
	}
	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			t.Setenv(tc.env, tc.envValue)
			result, err := checkKubectlVerb(tc.args.verb)
			if (err != nil) != tc.expectErr {
				t.Errorf("checkKubectlVerb() result error = %v, Expect Err is %v", err, tc.expectErr)
				return
			}
			if result != tc.expect {
				t.Errorf("checkKubectlVerb() result value = %v, Expect value is %v", result, tc.expect)
			}
		})
	}
}

func Test_checkKubectlApply(t *testing.T) {
	type args struct {
		args []string
	}
	testCases := []struct {
		name      string
		args      args
		env       string
		envValue  string
		expect    bool
		expectErr bool
	}{
		{name: "ApplyNotFile", args: args{
			args: []string{"apply"}},
			env: UnsafeResourceKinds, envValue: "NodeScalingRequest{nodeRequestType=delete},CardScalingRequest{scalingParameter.op=delete},CardScalingRequest{scalingParameter.op=replace}",
			expect: true, expectErr: false},
		{name: "ApplyRemoteFile", args: args{
			args: []string{"apply", "-f", "https://xxx.io/yyy.yaml"}},
			env: UnsafeResourceKinds, envValue: "NodeScalingRequest{nodeRequestType=delete},CardScalingRequest{scalingParameter.op=delete},CardScalingRequest{scalingParameter.op=replace}",
			expect: true, expectErr: false},
		{name: "ApplyRemoteFileLong", args: args{
			args: []string{"apply", "--filename=http://xxx.io/yyy.yaml"}},
			env: UnsafeResourceKinds, envValue: "NodeScalingRequest{nodeRequestType=delete},CardScalingRequest{scalingParameter.op=delete},CardScalingRequest{scalingParameter.op=replace}",
			expect: true, expectErr: false},
		{name: "ApplyStdin", args: args{
			args: []string{"apply", "-f", "-"}},
			env: UnsafeResourceKinds, envValue: "NodeScalingRequest{nodeRequestType=delete},CardScalingRequest{scalingParameter.op=delete},CardScalingRequest{scalingParameter.op=replace}",
			expect: true, expectErr: false},
		{name: "ApplyNoneExitstFile", args: args{
			args: []string{"apply", "-f", "foo"}},
			env: UnsafeResourceKinds, envValue: "NodeScalingRequest{nodeRequestType=delete},CardScalingRequest{scalingParameter.op=delete},CardScalingRequest{scalingParameter.op=replace}",
			expect: false, expectErr: true},
		{name: "ApplyNoneExitstRecursive", args: args{
			args: []string{"apply", "-f", "foo", "-R"}},
			env: UnsafeResourceKinds, envValue: "NodeScalingRequest{nodeRequestType=delete},CardScalingRequest{scalingParameter.op=delete},CardScalingRequest{scalingParameter.op=replace}",
			expect: false, expectErr: true},
		{name: "ApplyUnsafeFile", args: args{
			args: []string{"apply", "-f", "testdata/yaml/cr/csr/CardScalingRequest-delete.yaml"}},
			env: UnsafeResourceKinds, envValue: "NodeScalingRequest{nodeRequestType=delete},CardScalingRequest{scalingParameter.op=delete},CardScalingRequest{scalingParameter.op=replace}",
			expect: false, expectErr: false},
		{name: "ApplyUnsafeFileLong", args: args{
			args: []string{"apply", "--filename=testdata/yaml/cr/csr/CardScalingRequest-delete.yaml"}},
			env: UnsafeResourceKinds, envValue: "NodeScalingRequest{nodeRequestType=delete},CardScalingRequest{scalingParameter.op=delete},CardScalingRequest{scalingParameter.op=replace}",
			expect: false, expectErr: false},
		{name: "ApplyUnsafeFileEnvFile", args: args{
			args: []string{"apply", "-f", "testdata/yaml/cr/csr/CardScalingRequest-delete.yaml"}},
			env: UnsafeResourceKinds, envValue: getTestDataFile(t, "testdata/environment/unsafe-resources.txt"),
			expect: false, expectErr: false},
		{name: "ApplyUnsafeFileMany", args: args{
			args: []string{"apply", "-f", "testdata/yaml/cr/csr/CardScalingRequest-delete.yaml", "-f", "testdata/yaml/cr/nsr/NodeScalingRequest-delete.yaml"}},
			env: UnsafeResourceKinds, envValue: "NodeScalingRequest{nodeRequestType=delete},CardScalingRequest{scalingParameter.op=delete},CardScalingRequest{scalingParameter.op=replace}",
			expect: false, expectErr: false},
		{name: "ApplyUnsafeFileAndDir", args: args{
			args: []string{"apply", "-f", "testdata/yaml/cr/csr/CardScalingRequest-delete.yaml", "-f", "testdata/yaml/cr/nsr"}},
			env: UnsafeResourceKinds, envValue: "NodeScalingRequest{nodeRequestType=delete},CardScalingRequest{scalingParameter.op=delete},CardScalingRequest{scalingParameter.op=replace}",
			expect: false, expectErr: false},
		{name: "ApplyUnsafeDir", args: args{
			args: []string{"apply", "-f", "testdata/yaml/cr/csr"}},
			env: UnsafeResourceKinds, envValue: "NodeScalingRequest{nodeRequestType=delete},CardScalingRequest{scalingParameter.op=delete},CardScalingRequest{scalingParameter.op=replace}",
			expect: false, expectErr: false},
		{name: "ApplyUnsafeDirMany", args: args{
			args: []string{"apply", "-f", "testdata/yaml/cr/csr", "-f", "testdata/yaml/cr/nsr"}},
			env: UnsafeResourceKinds, envValue: "NodeScalingRequest{nodeRequestType=delete},CardScalingRequest{scalingParameter.op=delete},CardScalingRequest{scalingParameter.op=replace}",
			expect: false, expectErr: false},
		{name: "ApplyUnsafeDirRecursive", args: args{
			args: []string{"apply", "-f", "testdata/yaml/cr", "-R"}},
			env: UnsafeResourceKinds, envValue: "NodeScalingRequest{nodeRequestType=delete},CardScalingRequest{scalingParameter.op=delete},CardScalingRequest{scalingParameter.op=replace}",
			expect: false, expectErr: false},
		{name: "ApplyUnsafeDirRecursiveLong", args: args{
			args: []string{"apply", "-f", "testdata/yaml/cr", "--recursive"}},
			env: UnsafeResourceKinds, envValue: "NodeScalingRequest{nodeRequestType=delete},CardScalingRequest{scalingParameter.op=delete},CardScalingRequest{scalingParameter.op=replace}",
			expect: false, expectErr: false},
		{name: "ApplySafe1", args: args{
			args: []string{"apply", "-f", "testdata/yaml/cr/csr/CardScalingRequest-add.yaml"}},
			env: UnsafeResourceKinds, envValue: "NodeScalingRequest{nodeRequestType=delete},CardScalingRequest{scalingParameter.op=delete},CardScalingRequest{scalingParameter.op=replace}",
			expect: true, expectErr: false},
		{name: "ApplySafe2", args: args{
			args: []string{"apply", "-f", "testdata/yaml/cr/csr/CardScalingRequest-delete.yaml"}},
			env: UnsafeResourceKinds, envValue: "",
			expect: true, expectErr: false},
		{name: "NotApply", args: args{
			args: []string{"delete"}},
			env: UnsafeResourceKinds, envValue: "NodeScalingRequest{nodeRequestType=delete},CardScalingRequest{scalingParameter.op=delete},CardScalingRequest{scalingParameter.op=replace}",
			expect: true, expectErr: false},
	}
	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			t.Setenv(tc.env, tc.envValue)
			result, err := checkKubectlApply(tc.args.args)
			if (err != nil) != tc.expectErr {
				t.Errorf("checkKubectlApply() result error = %v, Expect Err is %v", err, tc.expectErr)
				return
			}
			if result != tc.expect {
				t.Errorf("checkKubectlApply() result value = %v, Expect value is %v", result, tc.expect)
			}
		})
	}
}

func Test_CheckSafe(t *testing.T) {
	type args struct {
		verb string
		args []string
	}
	type envs struct {
		env      string
		envValue string
	}
	testCases := []struct {
		name      string
		args      args
		envs      []envs
		expect    bool
		expectErr bool
	}{
		{name: "DryRunUnsafeResources", args: args{
			verb: "apply",
			args: []string{"apply", "-f", "testdata/yaml/cr/nsr/NodeScalingRequest-delete.yaml", "--dry-run=client"},
		}, envs: []envs{
			{env: UnsafeResourceKinds, envValue: "NodeScalingRequest{nodeRequestType=delete}"},
		}, expect: true, expectErr: false},
		{name: "DryRunUnsafeCommands", args: args{
			verb: "delete",
			args: []string{"delete", "pod", "--dry-run=client"},
		}, envs: []envs{
			{env: UnsafeKubectlCommands, envValue: "delete"},
		}, expect: true, expectErr: false},
		{name: "DryRunSafeCommands", args: args{
			verb: "get",
			args: []string{"get", "pod"},
		}, envs: []envs{
			{env: UnsafeKubectlCommands, envValue: "delete"},
		}, expect: true, expectErr: false},
		{name: "ApplyRemoteFile", args: args{
			verb: "apply",
			args: []string{"apply", "-f", "https://xxx.io/yyy.yaml"},
		}, envs: []envs{
			{env: UnsafeResourceKinds, envValue: "NodeScalingRequest{nodeRequestType=delete}"},
		}, expect: true, expectErr: false},
		{name: "ApplyStdin", args: args{
			verb: "apply",
			args: []string{"apply", "-f", "-"},
		}, envs: []envs{
			{env: UnsafeResourceKinds, envValue: "NodeScalingRequest{nodeRequestType=delete}"},
		}, expect: true, expectErr: false},
		{name: "SetUnsafeResourcesCsv", args: args{
			verb: "apply",
			args: []string{"apply", "-f", "testdata/yaml/cr/nsr/NodeScalingRequest-delete.yaml"},
		}, envs: []envs{
			{env: UnsafeResourceKinds, envValue: "NodeScalingRequest{nodeRequestType=delete}"},
		}, expect: false, expectErr: false},
		{name: "SetUnsafeResourcesFile", args: args{
			verb: "apply",
			args: []string{"apply", "-f", "testdata/yaml/cr/nsr/NodeScalingRequest-delete.yaml", "-f", "testdata/yaml/cr/csr"},
		}, envs: []envs{
			{env: UnsafeResourceKinds, envValue: "testdata/environment/unsafe-resources.txt"},
		}, expect: false, expectErr: false},
		{name: "SetUnsafeResourcesFileWithDirRecursive", args: args{
			verb: "apply",
			args: []string{"apply", "-f", "testdata/yaml/cr", "-R"},
		}, envs: []envs{
			{env: UnsafeResourceKinds, envValue: "testdata/environment/unsafe-resources.txt"},
		}, expect: false, expectErr: false},
		{name: "SetUnsafeResourcesWithSetUnsafeCommands", args: args{
			verb: "apply",
			args: []string{"apply", "-f", "testdata/yaml/cr/nsr/NodeScalingRequest-delete.yaml"},
		}, envs: []envs{
			{env: UnsafeResourceKinds, envValue: "NodeScalingRequest{nodeRequestType=delete}"},
			{env: UnsafeKubectlCommands, envValue: "apply"},
		}, expect: false, expectErr: false},
		{name: "SetUnsafeResourcesDiffer", args: args{
			verb: "apply",
			args: []string{"apply", "-f", "testdata/yaml/cr/nsr/NodeScalingRequest-create.yaml"},
		}, envs: []envs{
			{env: UnsafeResourceKinds, envValue: "NodeScalingRequest{nodeRequestType=delete}"},
		}, expect: true, expectErr: false},
		{name: "SetUnsafeResourcesDifferWithSetUnsafeCommands", args: args{
			verb: "apply",
			args: []string{"apply", "-f", "testdata/yaml/cr/nsr/NodeScalingRequest-create.yaml"},
		}, envs: []envs{
			{env: UnsafeResourceKinds, envValue: "NodeScalingRequest{nodeRequestType=delete}"},
			{env: UnsafeKubectlCommands, envValue: "apply"},
		}, expect: false, expectErr: false},
		{name: "SetUnsafeCommands", args: args{
			verb: "delete",
			args: []string{"delete", "-f", "testdata/yaml/cr/nsr/NodeScalingRequest-create.yaml"},
		}, envs: []envs{
			{env: UnsafeResourceKinds, envValue: "NodeScalingRequest{nodeRequestType=delete}"},
			{env: UnsafeKubectlCommands, envValue: "delete"},
		}, expect: false, expectErr: false},
		{name: "SetUnsafeCommandsDiffer", args: args{
			verb: "delete",
			args: []string{"delete", "-f", "testdata/yaml/cr/nsr/NodeScalingRequest-create.yaml"},
		}, envs: []envs{
			{env: UnsafeResourceKinds, envValue: "NodeScalingRequest{nodeRequestType=delete}"},
			{env: UnsafeKubectlCommands, envValue: "apply"},
		}, expect: true, expectErr: false},
		{name: "DefaultSafeCommands", args: args{
			verb: "delete",
			args: []string{"delete", "pod"},
		}, envs: []envs{
			{env: UnsafeKubectlCommands, envValue: ""},
		}, expect: true, expectErr: false},
	}
	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			for _, e := range tc.envs {
				t.Setenv(e.env, e.envValue)
			}
			result, err := CheckSafe(tc.args.verb, tc.args.args)
			if (err != nil) != tc.expectErr {
				t.Errorf("CheckSafe() result Err = %v, Expect Err is %v", err, tc.expectErr)
				return
			}
			if result != tc.expect {
				t.Errorf("CheckSafe() result value = %v, Expect value is %v", result, tc.expect)
			}
		})
	}
}
