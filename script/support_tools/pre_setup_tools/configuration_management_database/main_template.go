package main

import (
	"context"
	"flag"
	"fmt"
	"init-mgmt-db/gen/model"
	"init-mgmt-db/gen/query"
	"log"
	"os"
	"time"

	"gorm.io/driver/postgres"
	"gorm.io/gen/field"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
)

//nolint:funlen // this function is long but only used for tools
func main() {
	var password string
	flag.StringVar(&password, "password", "", "password of PostgreSQL.")
	flag.Parse()

	fmt.Printf("password: %s\n", password)
	dsn := "host=127.0.0.1 user=postgres password=" + password + " dbname=app port=5432 sslmode=prefer"
	newLogger := logger.New(
		log.New(os.Stdout, "\r\n", log.LstdFlags), // io writer
		logger.Config{
			SlowThreshold: time.Second, // Slow SQL threshold
			LogLevel:      logger.Info, // Log level
			Colorful:      true,
		},
	)
	db, err := gorm.Open(postgres.Open(dsn), &gorm.Config{
		Logger: newLogger,
	})
	if err != nil {
		panic(err)
	}

	sqlDB, err := db.DB()
	defer func() {
		if sqlDB != nil {
			if err = sqlDB.Close(); err != nil {
				fmt.Printf("Error closing database: %v\n", err)
			}
		}
	}()

	ctx := context.Background()
	qu := query.Use(db)
	const batchSize = 10

	// DCI物理インフラの拠点の名前。変更不要
	phy := &model.TPhysical{
		Name: "phy1",
	}
	q := qu.TPhysical
	rp, err := q.WithContext(ctx).
		Where(q.Name.Eq(phy.Name)).
		Assign(field.Attrs(phy)).
		FirstOrCreate()

        {{- range $i, $loc := .Location }}
        loc{{ add $i 1 }} := &model.TLocation{
		PhysicalInfraID: rp.ID,
		Location:        "{{ $loc }}", // 拠点名。環境に合わせて変更すること
	}
        {{- end }}

	ql := qu.TLocation
        {{- range $i, $_ := .Location }}
	ql.WithContext(ctx).Create(loc{{ add $i 1 }})
        {{- end }}

	// 拠点にあるスイッチの情報。
	// スイッチにログインしてVLANの設定やログ収集するために必要。
	// VLAN設計等の試験もする様な環境であれば、設定が必要
 	swList := []*model.TNwSwitch{
	{{- range $i, $sw := .NwSwitch }}
		{
			NwSwitchName: "{{ $sw.NwSwitchName }}",      // スイッチ名は意に設定可能
			Location:     "{{ locationName $sw.Location }}", // 拠点名
			NwIPAddress:  "{{ $sw.NwIPAddress }}",
			NwUser:       "{{ $sw.NwUser }}",
			Status:       {{ $sw.Status }},
			ProductInfo: `{{ nwSwitchProductInfo $sw.ProductInfo }}   `,
		},
	{{- end }}
	}
	qsw := qu.TNwSwitch
	if err := qsw.WithContext(ctx).CreateInBatches(swList, batchSize); err != nil {
		return
	}
	{{- range $i, $sw := .NwSwitch }}
        sw{{ add1 $i }}, _ := qsw.WithContext(ctx).Where(qsw.NwSwitchName.Eq("{{ $sw.NwSwitchName }}"), qsw.Location.Eq("{{ locationName $sw.Location }}")).First()
        {{- end }}

	// 上記のスイッチのポートごとのレコード
	// スイッチのVLAN設定等がないのであれば、使用しないので変更不要
	ports := []*model.TNwPort{
	{{- range .NwPort }}
            	{
			NwSwitchID:    {{ .NwSwitchID }},
                	InterfaceName: "{{ .InterfaceName }}",
        	},
	{{- end }}	
	}
	qport := qu.TNwPort
	if err := qport.WithContext(ctx).CreateInBatches(ports, batchSize); err != nil {
		return
	}

	// Information for MAAS
	maas := &model.TMaa{
		PhysicalInfraID: rp.ID,
		AccessURL:       "{{ .Maas.AccessURL }}",
		APIKey:          "{{ .Maas.APIKey }}",
		Status:          {{ .Maas.Status }},
		ProductInfo: `{{ maasProductInfo }}`,
	}
	qm := qu.TMaa
	qm.WithContext(ctx).Create(maas)

	// Information for PG-CDI
	// No changes needed if PG-CDI is not used in your environment
	extraParams := `{{ cdiExtraParams }}`
	c := &model.TCdi{
		CdiName:    "{{ .Cdi.Name }}",
		Location:   "{{ .Cdi.Location }}",
		RemoteHost: "{{ .Cdi.RemoteHost }}",
		RemoteUser: "{{ .Cdi.RemoteUser }}",
		GroupName:  "{{ .Cdi.GroupName }}",
		Status:     {{ .Cdi.Status }},
		ProductInfo: `{{ cdiProductInfo }}`,
		ExtraParameters: &extraParams,
	}
	qc := qu.TCdi
	qc.WithContext(ctx).Create(c)
	rc, _ := qc.WithContext(ctx).Where(qc.Location.Eq("{{ .Cdi.Location }}")).First()

	// PG-CDIのPCIe-Boxの情報
	boxIPAddress := "{{ .PcieBox.IPAddress }}"
	box := &model.TCdiBox{
		CdiID:     rc.CdiID,
		IPAddress: &boxIPAddress,
		Status:    {{ .PcieBox.Status }},
	}
	qb := qu.TCdiBox
	rb, _ := qb.WithContext(ctx).Assign(field.Attrs(box)).FirstOrCreate()

	// PG-CDIのPCIe-Boxにささっている100G NICの情報
	// PG-CDIを使わない環境であれば変更不要
	cnicList := []*model.TCdiNic{
        {{- range .PcieBox.Nic }}
        {
	        ResUUID:           "{{ .ResUUID }}",
	        ResName:           "{{ .ResName }}",
	        ApldataMacAddress: "{{ .Mac }}",
	        ApldataNwPortID:   {{ .NwPortID }},
	        CdiID:             rc.CdiID,
	        BoxID:             rb.ID,
	        Status:            {{ .Status }},
        },
        {{- end }}
	}
	qcn := qu.TCdiNic
	qcn.WithContext(ctx).CreateInBatches(cnicList, batchSize)

	// PG-CDIのPCIe-BoxにささっているGPUの情報
	// PG-CDIを使わない環境であれば変更不要
	cgpuList := []*model.TCdiGpu{
        {{- range .PcieBox.Gpu }}
        {
	        ResUUID: "{{ .ResUUID }}",
	        ResName: "{{ .ResName }}",
	        UUID:    "{{ .UUID }}",
	        CdiID:   rc.CdiID,
	        BoxID:   rb.ID,
	        Status:  {{ .Status }},
        },
        {{- end }}
	}
	qcg := qu.TCdiGpu
	qcg.WithContext(ctx).CreateInBatches(cgpuList, batchSize)

	// PG-CDIのPCIe-BoxにささっているSSDの情報
	// PG-CDIを使わない環境であれば変更不要
	cssdList := []*model.TCdiSsd{
        {{- range .PcieBox.Ssd }}
        {
	        ResUUID:   "{{ .ResUUID }}",
	        ResName:   "{{ .ResName }}",
	        StorageGb: {{ .StorageGb }},
	        CdiID:     rc.CdiID,
	        BoxID:     rb.ID,
	        Status:    {{ .Status }},
        },
        {{- end }}
	}
	qcs := qu.TCdiSsd
	qcs.WithContext(ctx).CreateInBatches(cssdList, batchSize)

        {{- range $i, $cp := .ComputePool }}
        {{- if $cp.Apldata }}
        appMacAddress{{ add $i 1 }} := "{{ $cp.Apldata.Mac }}"
        appNwPortID{{ add $i 1 }} := int32({{ $cp.Apldata.NwPortID }})
        appModel{{ add $i 1 }} := "{{ $cp.Apldata.NicModel }}"
        {{- end }}
        {{- end }}
	// CDI計算サーバの情報
	ccpList := []*model.TCdiComputePool{
                {{- range $i, $cp := .ComputePool }}
		{
			HostName:          "{{ $cp.HostName }}", //ユニークな任意のホスト名
			IpmiAddress:       "{{ $cp.IpmiAddress }}",
			IpmiUser:          "{{ $cp.IpmiUser }}",
			IpmiPassword:      "{{ $cp.IpmiPassword }}",
			MgrMacAddress:     "{{ $cp.MgrMac }}",
			HostMacAddress:    "{{ $cp.HostMac }}",
			HostNwPortID:      {{ $cp.HostNwPortID }},
			CniMacAddress:     "{{ $cp.CniMac }}",
			CniNwPortID:       {{ $cp.CniNwPortID }},
			{{- if $cp.Apldata }}
			ApldataMacAddress: &appMacAddress{{ add1 $i }}, //計算サーバにアプリデータ用NICが搭載されている場合のみ設定
			ApldataNwPortID:   &appNwPortID{{ add1 $i }},   //同上
			ApldataNicModel:   &appModel{{ add1 $i }},      //同上
                        {{- end }}
                        CdiID:             rc.CdiID,
			ResName:           "{{ $cp.ResName }}",
			CPUCores:          {{ $cp.CPUCores }},
			MemoryMb:          {{ $cp.MemoryMb }},
			Status:            {{ $cp.Status }},
			ProductInfo: `{
				"vendor": "{{ index $cp.ProductInfo "vendor" }}",
				"product_name": "{{ index $cp.ProductInfo "product_name" }}",
				"version": "{{ index $cp.ProductInfo "version" }}"
			}`,
		},
		{{- end }}
	}
	qccp := qu.TCdiComputePool
	qccp.WithContext(ctx).CreateInBatches(ccpList, batchSize)

{{- range $i, $c := .Cots }}
{{- if $c.Apldata }}
        ama{{ add $i 1 }} := "{{ $c.Apldata.Mac }}"
        anpi{{ add $i 1 }} := int32({{ $c.Apldata.NwPortID }})
        anm{{ add $i 1 }} := "{{ $c.Apldata.NicModel }}"
{{ end }}
{{- end }}

        cotsList := []*model.TCotsServerPool{
{{- range $i, $c := .Cots }}
        {
                HostName: "{{ $c.HostName }}",
                Location: "{{ $c.Location }}",
                IpmiAddress: "{{ $c.IpmiAddress }}",
                IpmiUser: "{{ $c.IpmiUser }}",
                IpmiPassword: "{{ $c.IpmiPassword }}",
                ServerRole: {{ $c.ServerRole }},
                DeploymentType: {{ $c.DeploymentType }},
                MgrMacAddress: "{{ $c.MgrMac }}",
                HostMacAddress: "{{ $c.HostMac }}",
                HostNwPortID: {{ $c.HostNwPortID }},
                CniMacAddress: "{{ $c.CniMac }}",
                CniNwPortID: {{ $c.CniNwPortID }},
{{- if $c.Apldata }}
                ApldataMacAddress: &ama{{ add $i 1 }},
                ApldataNwPortID: &anpi{{ add $i 1 }},
                ApldataNicModel: &anm{{ add $i 1 }},
{{- end }}
                CPUCores: {{ $c.CPUCores }},
                MemoryMb: {{ $c.MemoryMb }},
                StorageGb: {{ $c.StorageGb }},
                Status: {{ $c.Status }},
ProductInfo: `{{ productInfo $c.ProductInfo }}`,
        },
{{- end }}
        }
	qcots := qu.TCotsServerPool
	qcots.WithContext(ctx).CreateInBatches(cotsList, batchSize)

	{{- range $worker, $var := .WorkerMap }}
	{{ $var }}, _ := qcots.WithContext(ctx).Where(qcots.HostName.Eq("{{ $worker }}")).First()
	{{- end }}

	cotsGpuList := []*model.TCotsServerGpu{
	{{- range .CotsGpu }}
	   	 {
			ServerID: {{ index $.WorkerMap .Worker }}.ServerID,
    			UUID:     "{{ .UUID }}",
    			Model:    "{{ .Model }}",
    			Status:   {{ .Status }},
		 },
	{{- end }}
	}
	qcotsg := qu.TCotsServerGpu
	qcotsg.WithContext(ctx).CreateInBatches(cotsGpuList, batchSize)

	osInfo := &model.TOsInfo{
		OsDistribution: "rhel",       // 環境によって異なるので、MAASに登録されているOSイメージを参照
		OsVersion:      "9.6-custom", // 同上
		LoginUser:      "cloud-user",
	}
	qo := qu.TOsInfo
	if err := qo.WithContext(ctx).Create(osInfo); err != nil {
		return
	}
}
