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
