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

package prompt

import (
	"bufio"
	"fmt"
	"os"
	"strings"

	"k8s.io/klog/v2"

	"kubectl-confirmation/pkg/execution"
)

func GetUserConfirmation(kubectlVerb string) bool {
	currContext := "Unknown"
	if cmdOut, err := execution.ExecCmd("kubectl", "config", "current-context"); err != nil {
		klog.Error(err)
	} else {
		currContext = strings.ReplaceAll(cmdOut, "\n", "")
	}

	keyRead := bufio.NewReader(os.Stdin)
	fmt.Printf("You are running a %s against current-context %s, continue? [y/n] ", kubectlVerb, currContext)
	keyInput, err := keyRead.ReadString('\n')
	if err != nil {
		return false
	}

	return strings.ToLower(strings.TrimSpace(keyInput)) == "y"
}
