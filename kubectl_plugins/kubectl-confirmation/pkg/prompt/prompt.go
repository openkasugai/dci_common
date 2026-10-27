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
