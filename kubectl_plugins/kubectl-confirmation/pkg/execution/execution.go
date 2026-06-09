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

package execution

import (
	"os"
	"os/exec"
	"syscall"
)

func ExecCmd(cmd string, args ...string) (string, error) {
	cmdPath, err := exec.LookPath(cmd)
	if err != nil {
		return "", err
	}
	// os/exec creates a child process.
	cmdOut, err := exec.Command(cmdPath, args...).Output()
	if err != nil {
		return "", err
	}

	return string(cmdOut), nil
}

func ExecKubectl(args []string) error {
	cmdPath, err := exec.LookPath("kubectl")
	if err != nil {
		return err
	}
	cmdArgv := append([]string{cmdPath}, args...)

	// syscall.Exec replaces a process.
	return syscall.Exec(cmdPath, cmdArgv, os.Environ())
}
