package main

import (
	"encoding/json"
	"fmt"
	"os"
	"strings"
	"text/template"

	"gopkg.in/yaml.v3"
)

/*
====================================
Config 定義
====================================
*/

type Config struct {
	Location    []string            `yaml:"location"`
	Cots        []Cots              `yaml:"cots"`
	Maas        MaasConfig          `yaml:"maas"`
	Cdi         CdiConfig           `yaml:"cdi"`
	PcieBox     PcieBoxConfig       `yaml:"pcie_box"`
	ComputePool []ComputePoolConfig `yaml:"compute_pool"`
	NwSwitch    []NwSwitchConfig    `yaml:"nw_switch"`
	NwPort      []NwPortConfig      `yaml:"nw_port"`
	CotsGpu     []CotsGpuConfig     `yaml:"cots_gpu"`

	WorkerMap map[string]string `yaml:"-"`
}

/*
====================================
Compute Pool
====================================
*/

type ComputePoolConfig struct {
	HostName     string `yaml:"host_name"`
	IpmiAddress  string `yaml:"ipmi_address"`
	IpmiUser     string `yaml:"ipmi_user"`
	IpmiPassword string `yaml:"ipmi_password"`
	MgrMac       string `yaml:"mgr_mac"`
	HostMac      string `yaml:"host_mac"`
	HostNwPortID int    `yaml:"host_nw_port_id"`
	CniMac       string `yaml:"cni_mac"`
	CniNwPortID  int    `yaml:"cni_nw_port_id"`
	ResName      string `yaml:"res_name"`
	CPUCores     int    `yaml:"cpu_cores"`
	MemoryMb     int    `yaml:"memory_mb"`
	Status       int    `yaml:"status"`

	ProductInfo map[string]interface{} `yaml:"product_info"`

	Apldata *struct {
		Mac      string `yaml:"mac"`
		NwPortID int    `yaml:"nw_port_id"`
		NicModel string `yaml:"nic_model"`
	} `yaml:"apldata"`
}

/*
====================================
MAAS
====================================
*/

type MaasConfig struct {
	AccessURL   string                 `yaml:"access_url"`
	APIKey      string                 `yaml:"api_key"`
	Status      int                    `yaml:"status"`
	ProductInfo map[string]interface{} `yaml:"product_info"`
}

/*
====================================
CDI
====================================
*/

type CdiConfig struct {
	Name        string                 `yaml:"name"`
	Location    string                 `yaml:"location"`
	RemoteHost  string                 `yaml:"remote_host"`
	RemoteUser  string                 `yaml:"remote_user"`
	GroupName   string                 `yaml:"group_name"`
	Status      int                    `yaml:"status"`
	ProductInfo map[string]interface{} `yaml:"product_info"`
	ExtraParams map[string]interface{} `yaml:"extra_parameters"`
}

/*
====================================
PCIe_Box
====================================
*/

type PcieBoxConfig struct {
	IPAddress string `yaml:"ip_address"`
	Status    int    `yaml:"status"`

	Nic []PcieNic `yaml:"nic"`
	Gpu []PcieGpu `yaml:"gpu"`
	Ssd []PcieSsd `yaml:"ssd"`
}

type PcieNic struct {
	ResUUID  string `yaml:"res_uuid"`
	ResName  string `yaml:"res_name"`
	Mac      string `yaml:"mac"`
	NwPortID int    `yaml:"nw_port_id"`
	Status   int    `yaml:"status"`
}

type PcieGpu struct {
	ResUUID string `yaml:"res_uuid"`
	ResName string `yaml:"res_name"`
	UUID    string `yaml:"uuid"`
	Status  int    `yaml:"status"`
}

type PcieSsd struct {
	ResUUID   string `yaml:"res_uuid"`
	ResName   string `yaml:"res_name"`
	StorageGb int    `yaml:"storage_gb"`
	Status    int    `yaml:"status"`
}

/*
====================================
COTS
====================================
*/

type Cots struct {
	HostName       string                 `yaml:"host_name"`
	Location       string                 `yaml:"location"`
	IpmiAddress    string                 `yaml:"ipmi_address"`
	IpmiUser       string                 `yaml:"ipmi_user"`
	IpmiPassword   string                 `yaml:"ipmi_password"`
	ServerRole     int                    `yaml:"server_role"`
	DeploymentType int                    `yaml:"deployment_type"`
	MgrMac         string                 `yaml:"mgr_mac"`
	HostMac        string                 `yaml:"host_mac"`
	HostNwPortID   int                    `yaml:"host_nw_port_id"`
	CniMac         string                 `yaml:"cni_mac"`
	CniNwPortID    int                    `yaml:"cni_nw_port_id"`
	CPUCores       int                    `yaml:"cpu_cores"`
	MemoryMb       int                    `yaml:"memory_mb"`
	StorageGb      int                    `yaml:"storage_gb"`
	Status         int                    `yaml:"status"`
	ProductInfo    map[string]interface{} `yaml:"product_info"`
	Apldata        *struct {
		Mac      string `yaml:"mac"`
		NwPortID int    `yaml:"nw_port_id"`
		NicModel string `yaml:"nic_model"`
	} `yaml:"apldata"`
}

/*
====================================
NW_SWITCH
====================================
*/

type NwSwitchConfig struct {
	NwSwitchName string                 `yaml:"nw_switch_name"`
	Location     string                 `yaml:"location"`
	NwIPAddress  string                 `yaml:"nw_ip_address"`
	NwUser       string                 `yaml:"nw_user"`
	Status       int                    `yaml:"status"`
	ProductInfo  map[string]interface{} `yaml:"product_info"`
}

/*
====================================
NW_PORT
====================================
*/

type NwPortConfig struct {
	NwSwitchID    string `yaml:"nw_switch_id"`
	InterfaceName string `yaml:"interface_name"`
}

/*
====================================
COTS_GPU
====================================
*/

type CotsGpuConfig struct {
	Worker string `yaml:"worker"`
	UUID   string `yaml:"uuid"`
	Model  string `yaml:"model"`
	Status int    `yaml:"status"`
}

func main() {

	/*
		--------------------------------
		YAML 読み込み
		--------------------------------
	*/

	b, err := os.ReadFile("config.yaml")
	if err != nil {
		panic(err)
	}

	var cfg Config
	if err := yaml.Unmarshal(b, &cfg); err != nil {
		panic(err)
	}

	workerMap := make(map[string]string)
	index := 1

	for _, gpu := range cfg.CotsGpu {
		if _, ok := workerMap[gpu.Worker]; !ok {
			workerMap[gpu.Worker] = fmt.Sprintf("worker%d", index)
			index++
		}
	}

	cfg.WorkerMap = workerMap

	/*
		--------------------------------
		MAAS JSON化
		--------------------------------
	*/

	maasProductJSON, err := json.MarshalIndent(cfg.Maas.ProductInfo, "", "  ")
	if err != nil {
		panic(err)
	}
	maasProductStr := string(maasProductJSON)

	/*
		--------------------------------
		CDI JSON化
		--------------------------------
	*/

	cdiProductJSON, err := json.MarshalIndent(cfg.Cdi.ProductInfo, "", "  ")
	if err != nil {
		panic(err)
	}
	cdiProductStr := string(cdiProductJSON)

	extraJSON, err := json.MarshalIndent(cfg.Cdi.ExtraParams, "", "  ")
	if err != nil {
		panic(err)
	}
	extraStr := string(extraJSON)

	/*
		--------------------------------
		ComputePool JSON化
		--------------------------------
	*/

	computePoolJSON, err := json.MarshalIndent(cfg.ComputePool, "", "  ")
	if err != nil {
		panic(err)
	}
	computePoolStr := string(computePoolJSON)

	/*
		--------------------------------
		NW Switch JSON化
		--------------------------------
	*/

	nwSwitchJSON, err := json.MarshalIndent(cfg.NwSwitch, "", "  ")
	if err != nil {
		panic(err)
	}
	nwSwitchStr := string(nwSwitchJSON)

	/*
		--------------------------------
		テンプレート関数
		--------------------------------
	*/

	funcMap := template.FuncMap{
		"add": func(a, b int) int { return a + b },

		"add1": func(i int) int {
			return i + 1
		},

		"maasProductInfo": func() string {
			return maasProductStr
		},
		"cdiProductInfo": func() string {
			return cdiProductStr
		},
		"cdiExtraParams": func() string {
			return extraStr
		},
		"computePoolInfo": func() string {
			return computePoolStr
		},
		"nwSwitchInfo": func() string {
			return nwSwitchStr
		},
		"nwSwitchProductInfo": func(m map[string]interface{}) string {
			b, err := json.MarshalIndent(m, "", "  ")
			if err != nil {
				panic(err)
			}
			return string(b)
		},
		"productInfo": func(m map[string]interface{}) string {

			b, err := json.MarshalIndent(m, "", "  ")
			if err != nil {
				panic(err)
			}
			return string(b)
		},
		"locationName": func(s string) string {
			location := strings.TrimPrefix(s, "loc")
			if location != s && len(location) >= 9 && strings.EqualFold(location[len(location)-9:], ".location") {
				num := location[:len(location)-9]
				return "dc" + num
			}
			return s
		},
	}

	/*
		--------------------------------
		テンプレート読み込み
		--------------------------------
	*/

	t := template.Must(
		template.New("main").
			Funcs(funcMap).
			ParseFiles("main_template.go"),
	)

	/*
		--------------------------------
		実行
		--------------------------------
	*/

	if err := t.ExecuteTemplate(os.Stdout, "main_template.go", cfg); err != nil {
		panic(err)
	}
}
