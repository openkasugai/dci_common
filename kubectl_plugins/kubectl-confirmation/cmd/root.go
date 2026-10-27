package cmd

import (
	"os"

	"github.com/spf13/cobra"
	"k8s.io/klog/v2"

	"kubectl-confirmation/pkg/execution"
	"kubectl-confirmation/pkg/prompt"
	"kubectl-confirmation/pkg/safety"
)

// rootCmd represents the base command when called without any subcommands
var rootCmd = &cobra.Command{
	Use:                "confirmation",
	Short:              "A kubectl plugin to query users for Verb and Resource reflections.",
	Long:               "A kubectl plugin to query users for Verb and Resource reflections.",
	Args:               cobra.ArbitraryArgs,                          // Accept any number of arguments
	DisableFlagParsing: true,                                         // When true, skip flag parsing and pass all arguments directly to args.
	FParseErrWhitelist: cobra.FParseErrWhitelist{UnknownFlags: true}, // Handling undefined flags as arguments
	RunE: func(cmd *cobra.Command, args []string) error {
		kubectlVerb := ""
		if len(args) > 0 {
			kubectlVerb = args[0]
		}
		isSafe, err := safety.CheckSafe(kubectlVerb, args)
		if err != nil {
			return err
		}
		if !isSafe {
			if !prompt.GetUserConfirmation(kubectlVerb) {
				klog.Info("Not running command.")
				os.Exit(0)
			}
		}
		return execution.ExecKubectl(args)
	},
}

// Execute adds all child commands to the root command and sets flags appropriately.
// This is called by main.main(). It only needs to happen once to the rootCmd.
func Execute() {
	err := rootCmd.Execute()
	if err != nil {
		klog.Error(err)
		os.Exit(1)
	}
}

func init() {
}
