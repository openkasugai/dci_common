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

// Definition of Environment Variables
const (
	// UnsafeResourceKinds is a csv of commands or a path to a file containing a set of unsafe resource kind
	UnsafeResourceKinds = "UNSAFE_RESOURCE_KINDS"
	// UnsafeKubectlCommands is a csv of commands or a path to a file containing a set of unsafe commands
	UnsafeKubectlCommands = "UNSAFE_KUBECTL_COMMANDS"
)
