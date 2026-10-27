package safety

// Definition of Environment Variables
const (
	// UnsafeResourceKinds is a csv of commands or a path to a file containing a set of unsafe resource kind
	UnsafeResourceKinds = "UNSAFE_RESOURCE_KINDS"
	// UnsafeKubectlCommands is a csv of commands or a path to a file containing a set of unsafe commands
	UnsafeKubectlCommands = "UNSAFE_KUBECTL_COMMANDS"
)
