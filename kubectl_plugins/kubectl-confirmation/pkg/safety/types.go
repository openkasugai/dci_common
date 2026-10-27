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
