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

type Void struct{}

type Verbs struct {
	verb map[string]Void
}

type Resources struct {
	resource map[string]map[string]map[string]Void
}

func (v *Verbs) Add(command string) {
	if command != "" {
		v.verb[command] = Empty
	}
}

func (v *Verbs) Contains(command string) bool {
	_, isExist := v.verb[command]
	return isExist
}

func (r *Resources) Add(kind, spec, specValue string) {
	if kind != "" && spec != "" && specValue != "" {
		if r.resource[kind] == nil {
			r.resource[kind] = make(map[string]map[string]Void)
		}
		if r.resource[kind][spec] == nil {
			r.resource[kind][spec] = make(map[string]Void)
		}
		r.resource[kind][spec][specValue] = Empty
	}
}

func (r *Resources) Contains(kind, spec, specValue string) bool {
	_, isExist := r.resource[kind][spec][specValue]
	return isExist
}

var (
	Empty          = Void{}
	EmptyVerbs     = Verbs{}
	EmptyResources = Resources{}
)
