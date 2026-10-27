# DCI-2.0 Parameter Sheet

This document compiles the information (parameters) required for the DCI Operator to construct the DCI Management Cluster and the DCI Tenant Logical Infrastructure.

> **Note:** This document is a fill-in template. Do not commit copies containing actual IP addresses, passwords, or other real values to a public repository.

## 1. List of DHRC materials used and their main versions

https://github.com/openkasugai/

| repository/OSS | tag /version |
|---|---|
| dci_manager | v1.0.0 |
| dci_physical_infrastructure | v1.0.0 |
| dci_tenant_infrastructure | v1.0.0 |
| dci_common | v1.0.0 |
| kubernetes | 1.34.8 |
| go | 1.26.2 |
| helm | 4.0.4 |
| velero | 1.17.1 |
| Other OSS | Refer to the separate OSS list |

## 2. Address / Account Info

### Operation Terminal

| Operation Terminal | Hostname | Manager NW Management IP | User / Password |
|---|---|---|---|
| DCI Operator Operation Terminal |  |  |  |
| Tenant Operator Operation Terminal |  |  |  |

### External Storage (NFS)

| External Storage | Hostname | Manager NW Management IP | User / Password | Export Directory Path |
|---|---|---|---|---|
| NFS Server (VM) |  |  |  |  |

### External Storage (Backup)

| External Storage | Hostname | Manager NW Management IP | User / Password | MINIO Info: IP Address | MINIO Info: Port Number | MINIO Info: aws_access_key_id | MINIO Info: aws_secret_access_key | MINIO Info: Bucket Name |
|---|---|---|---|---|---|---|---|---|
| Backup Server (VM) |  |  |  |  |  |  |  |  |

### Various servers

| Server | IP address or server name | Notes |
|---|---|---|
| NTP Server |  |  |
| DNS Server |  |  |
| Bastion Server (BASTION_IP) |  | <- Harbor/Grafana bastion |

| Server | Yes / No | IP address or server name | Notification email address |
|---|---|---|---|
| SMTP Server |  |  |  |

### NW Info

DCI System NW C Info (COTS#3)

| # | NW | CIDR | Default | Notes |
|---|---|---|---|---|
| 1 | Manager NW |  |  |  |
| 2 | Host NW |  |  |  |
| 3 | CNI NW |  |  |  |
| 4 | Application Data NW |  |  |  |
| 5 | For k8s Pod |  | 10.245.0.0/16 |  |
| 6 | For k8s service |  | 10.96.0.0/12 |  |
| 7 | For Application Pod 2nd-NIC (SR-IOV network operater) |  | 192.168.1.64/26 | Anything is fine as long as it does not overlap with others; the netmask depends on the application |

### Access Info (for DCI management)

| # | DCI Management Server | Hostname | IPMI/BMC IP | Manager NW MAC | Manager NW IP | Interface name | Redundancy VIP (CP) | Redundancy VIP (LB_VIP) | User / Password (IPMI/BMC) | User / Password (HW management, etc.) |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | DCI Management VM Host Server |  |  | - |  |  | - | - |  |  |
| 2 | DCI Management Cluster Control Plane1 |  |  | - |  |  | (Assign VIP) | (Assign a VIP different from the one for CP) |  |  |
| 3 | DCI Management Cluster Control Plane2 |  |  | - |  |  | (Assign VIP) | (Assign a VIP different from the one for CP) |  |  |
| 4 | DCI Management Cluster Control Plane3 |  |  | - |  |  | (Assign VIP) | (Assign a VIP different from the one for CP) |  |  |
| 5 | DCI Management Cluster node1 |  |  | - |  |  | - | - |  |  |
| 6 | DCI Management Cluster node2 |  |  | - |  |  | - | - |  |  |
| 7 | MAAS Server |  |  | - |  |  | - | - |  |  |

*Note: Assign a single common redundancy VIP shared by Control Plane 1-3.*

### Access Info (for DCI Tenant Logical Infrastructure)

| # | DCI Tenant Logical Infrastructure Server | Hostname | IPMI/BMC IP | Manager NW MAC | Manager NW IP | Redundancy VIP (CP) | Redundancy VIP (LB_VIP) | User / Password (IPMI/BMC) | User / Password (HW management, etc.) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | COTS Server (Control Plane) |  |  |  |  | (Assign a VIP different from the one for CP) | (Assign a VIP different from the one for CP) |  |  |
| 2 | COTS Server (Control Plane) |  |  |  |  | (Assign a VIP different from the one for CP) | (Assign a VIP different from the one for CP) |  |  |
| 3 | COTS Server (Control Plane) |  |  |  |  | (Assign a VIP different from the one for CP) | (Assign a VIP different from the one for CP) |  |  |
| 4 | COTS Server |  |  |  |  | - | - |  |  |
| 5 | Compute Server |  |  |  |  | - | - |  |  |
| 6 | : (continue for as many entries as needed) |  |  |  |  | - | - |  |  |

*Note: Assign a single common redundancy VIP shared by Control Plane 1-3.*

### Account information for DCI Management Cluster construction

| # | OSS | User | Password | Default: User | Default: Password | Default: database name |
|---|---|---|---|---|---|---|
| 1 | DCI Management Cluster Harbor |  |  | admin | Harbor12345 | - |
| 2 | DCI Management Cluster Grafana |  |  | admin | prom-operator | - |
| 3 | Configuration Management DB PostgreSQL |  |  | postgres | (secret management) | app |
| 4 | MAAS |  |  | admin | password |  |

### Account information for Tenant Logical Infrastructure construction

| # | OSS | User | Password |
|---|---|---|---|
| 1 | DCI Tenant Logical Infrastructure Harbor |  |  |
| 2 | DCI Management Cluster Grafana |  |  |

### OS RHEL license info

| # | Item | Value |
|---|---|---|
| 1 | RHEL activation-key |  |
| 2 | RHEL organization |  |

## 3. Configuration Management DB Info

Information required for the Configuration Management DB

Used in main.go

### 1. TPhysical (Physical Infrastructure Info)

Physical infrastructure location name

Table name: `t_physical`

| id | Column | Meaning | Example | Setting Value | Location in main.go |
|---|---|---|---|---|---|
| 1 | name | Physical infrastructure name (unique name) | phy1 | phy1 | // Name of the DCI physical infrastructure.<br>Inside phy := &amp;model.TPhysical{} |
|  | description | Description (if necessary) | (optional) |  |  |

### 2. TLocation (Location Info)

List all locations where physical infrastructure exists (below is an example of 2 locations)

Table name: `t_location`

| id | Column | Meaning | Example | Setting Value | Location in main.go |
|---|---|---|---|---|---|
| 1 | Location1 | Installation location name (unique name) | dc1 | dc1 | Inside loc1 := &amp;model.TLocation{}.<br>Describe separate variables (loc1, loc2) for the number of locations |
|  | description | Description (if necessary) | (optional) |  |  |
| 2 | Location2 | When there are multiple locations for physical infrastructure, the installation location name (unique name) | dc2 | dc2 |  |
|  | description | Description (if necessary) | (optional) |  |  |

(Continue in the same way for as many entries as needed)

### 3. TNwSwitch (Network Switch)

Describe the SW device information used for HOST/CNI/APPDATA, and the information of all SWs controlled from DHRC

Table name: `t_nw_switch`

| id | Column | Meaning | Example | Setting Value | Location in main.go |
|---|---|---|---|---|---|
| 1 | nw_switch_id | UUID (auto-generated) | UUID-XXXXXXX1 | No change needed (auto-generated) | Inside swList := []*model.TNwSwitch{}.<br>In list format, describe for the number of switches.<br>Note: Not in the parameter sheet, but status is fixed to "0".<br>In main.go, after setting the list, for the number of switches<br>sw1, _ := qsw.WithContext(ctx).Where(...<br>sw2, _ := qsw.WithContext(ctx).Where(...<br>:<br>describe. |
|  | NwSwitchName | SW name | l2-switch-host01 |  |  |
|  | Location | Specify the installation location as a variable | dc1 |  | Note: Specify the location in the form loc1.Location.<br> Not a string |
|  | NwIPAddress | Management IP address | 172.18.195.239 |  |  |
|  | NwUser | Management User | user1 |  |  |
|  | product_info.vendor | Vendor | edgecore networks |  |  |
|  | product_info.product_name | Product name | AS4625-54T |  |  |
|  | product_info.os | NOS | Edgecore SONiC |  |  |
|  | product_info.version | Version | none |  |  |
| 2 | nw_switch_id | UUID (auto-generated) | UUID-XXXXXXX2 | No change needed (auto-generated) |  |
|  | NwSwitchName | SW name | l2-switch-cni01 |  |  |
|  | Location | Installation location | dc1 |  | Specify as a variable (such as loc1.Location) |
|  | NwIPAddress | Management IP address | 172.18.195.239 |  |  |
|  | NwUser | Management User | user1 |  |  |
|  | product_info.vendor | Vendor | edgecore networks |  |  |
|  | product_info.product_name | Product name | AS4625-54T |  |  |
|  | product_info.os | NOS | Broadcom SONiC |  |  |
|  | product_info.version | Version | none |  |  |
| 3 | nw_switch_id | UUID (auto-generated) | UUID-XXXXXXX3 | No change needed (auto-generated) |  |
|  | NwSwitchName | SW name | l2-switch-app01 |  |  |
|  | Location | Installation location | dc1 |  | Specify as a variable (such as loc1.Location) |
|  | NwIPAddress | Management IP address | 172.18.195.239 |  |  |
|  | NwUser | Management User | user1 |  |  |
|  | product_info.vendor | Vendor | edgecore networks |  |  |
|  | product_info.product_name | Product name | DCS208/AS5812-54X |  |  |
|  | product_info.os | NOS | Edgecore SONiC |  |  |
|  | product_info.version | Version | none |  |  |

(Continue in the same way for as many entries as needed)

### 4. TNwPort (NW Port)

List of NICs (HOST/CNI/APPDATA) of all servers used for tenants, and the connected destination SW IDs and destination SW interfaces (all SWs used for HOST/CNI/APPDATA)

Table name: `t_nw_port`

| id | Column | Meaning | Example | Setting Value | Location in main.go |
|---|---|---|---|---|---|
| 1 | NwSwitchID | NwSwitchID of the registered switch | UUID-XXXXXXX1 |  | Inside ports := []*model.TNwPort{}.<br>Specify in the format NwSwitchID:    sw1.NwSwitchID,.<br>In list format, describe for the number of ports.<br>Note: In main.go the variables are filled in.<br>Note: The sw1 variable also needs to be changed.<br>  There is a place where the name is specified within the variable. |
|  | InterfaceName | I/F name: e.g., Ethernet0. The I/F name specified when configuring VLAN | Ethernet0 |  |  |
| 2 | NwSwitchID | NwSwitchID of the registered switch | UUID-XXXXXXX2 |  | Set as a variable (such as sw1.NwSwitchID, sw2.NwSwitchID, sw3.NwSwitchID) |
|  | InterfaceName | I/F name: e.g., Ethernet0. The I/F name specified when configuring VLAN | Ethernet0 |  |  |
| 3 | NwSwitchID | NwSwitchID of the registered switch | UUID-XXXXXXX3 |  | Set as a variable (such as sw1.NwSwitchID, sw2.NwSwitchID, sw3.NwSwitchID) |
|  | InterfaceName | I/F name: e.g., Ethernet0. The I/F name specified when configuring VLAN | Ethernet0 |  |  |
| 4 | NwSwitchID | NwSwitchID of the registered switch | UUID-XXXXXXX1 |  | Set as a variable (such as sw1.NwSwitchID, sw2.NwSwitchID, sw3.NwSwitchID) |
|  | InterfaceName | I/F name: e.g., Ethernet0. The I/F name specified when configuring VLAN | Ethernet4 |  |  |
| 5 | NwSwitchID | NwSwitchID of the registered switch | UUID-XXXXXXX2 |  | Set as a variable (such as sw1.NwSwitchID, sw2.NwSwitchID, sw3.NwSwitchID) |
|  | InterfaceName | I/F name: e.g., Ethernet0. The I/F name specified when configuring VLAN | Ethernet4 |  |  |
| 6 | NwSwitchID | NwSwitchID of the registered switch | UUID-XXXXXXX3 |  | Set as a variable (such as sw1.NwSwitchID, sw2.NwSwitchID, sw3.NwSwitchID) |
|  | InterfaceName | I/F name: e.g., Ethernet0. The I/F name specified when configuring VLAN | Ethernet10 |  |  |

(Continue in the same way for as many entries as needed)

### 5. TMaa (MAAS Info)

Table name: `t_maas`

| id | Column | Meaning | Example | Setting Value | Location in main.go |
|---|---|---|---|---|---|
| 1 | physical_infra_id | Specify the ID of the physical infrastructure controlled by MAAS as a variable | 1 |  | Inside maas := &amp;model.TMaa{}.<br>The PhysicalInfraID: rp.ID part |
|  | AccessURL | MAAS API URL | http://172.18.195.29:5240/MAAS/api/2.0/ |  |  |
|  | APIKey | MAAS API key | &lt;Describe the API key confirmed in the MAAS GUI&gt; |  |  |
|  | product_info.vendor | Vendor | canonical | canonical | Fixed |
|  | product_info.product_name | Product name | MAAS | MAAS | Fixed |
|  | product_info.version | Version | 3.6 | 3.6 | Fixed |

### 6. TCdi (CDI Info)

Table name: `t_cdi` Note: The setting differs between v2.0 and v1.1

#### (1) For CDI Management Software v2.0

| cdi_id | Column | Meaning | Example | Setting Value | Location in main.go |
|---|---|---|---|---|---|
| 1 | CdiName | Identifier (unique name such as cdi_v2.0) | cdi_v1.1 |  | Inside c := &amp;model.TCdi{}.<br>Modify extraParams as needed as well. |
|  | Location | Location (such as dc1) | dc1 |  |  |
|  | RemoteHost | Linux Client PC IP address | 172.18.11.111 |  |  |
|  | RemoteUser | Linux Client PC login user | ubuntu |  |  |
|  | GroupName | Resource group name | group0 | group0 | Fixed |
|  | product_info.vendor | Vendor | fujitsu |  |  |
|  | product_info.product_name | Product name | PRIMERGY CDI |  |  |
|  | product_info.version | CDI Management Software version | 1.1 | 2.0 | Fixed |
|  | extra_parameters.cdi_user | username at the time of cdictl -u $URL auth login on the Linux Client PC | cdiadmin | dhrcsystem | Fixed |
|  | extra_parameters.cdi_password | password at the time of cdictl -u $URL auth login on the Linux Client PC | ** |  |  |
|  | extra_parameters.director_password | Password of the Director login ID (liqadmin) (password specified with the -D option of the hhchk command) | ** |  |  |
|  | extra_parameters.cdi_host | IP address of the CDI Management Software (host OS) | 172.18.195.205 |  |  |
|  | extra_parameters.cdi_host_user | User of the CDI Management Server (host OS) | *** |  |  |
|  | extra_parameters.cdi_host_password | Password of the CDI Management Server (host OS) (password specified with the -F option of the hhchk command) | *** |  |  |
|  | extra_parameters.cdi_guest | IP address of the CDI Management Software (guest OS) | 172.18.195.205 |  |  |
|  | extra_parameters.cdi_guest_user | User of the CDI Management Software (guest OS) | cdiadmin |  |  |
|  | extra_parameters.cdi_guest_password | Password of the CDI Management Software (guest OS) | *** |  |  |
|  | extra_parameters.cdi_host_password | root password of CDI Management Server (host) | *** |  |  |

#### (2) For CDI Management Software v1.1

| cdi_id | Column | Meaning | Example | Setting Value | Location in main.go |
|---|---|---|---|---|---|
| 1 | CdiName | Identifier (unique name such as cdi_v1.1) | cdi_v1.1 |  | Inside c := &amp;model.TCdi{}.<br>Modify extraParams as needed as well. |
|  | Location | Location (such as dc1) | dc1 |  |  |
|  | RemoteHost | Linux Client PC IP address | 172.18.11.111 |  |  |
|  | RemoteUser | Linux Client PC login user | ubuntu |  |  |
|  | GroupName | Resource group name | group0 | group0 | Fixed |
|  | product_info.vendor | Vendor | fujitsu |  |  |
|  | product_info.product_name | Product name | PRIMERGY CDI |  |  |
|  | product_info.version | CDI Management Software version | 1.1 | 1.1 | Fixed |
|  | extra_parameters.cdi_user | username at the time of cdictl -u $URL auth login on the Linux Client PC | cdiadmin | dhrcsystem | Fixed |
|  | extra_parameters.cdi_password | password at the time of cdictl -u $URL auth login on the Linux Client PC | ** |  |  |
|  | extra_parameters.director_password | Password of the Director login ID (liqadmin) (password specified with the -D option of the hhchk command) | ** |  |  |
|  | extra_parameters.cdi_host_password | root password of the CDI Management Server (host OS) (password specified with the -F option of the hhchk command) | *** |  |  |
|  | extra_parameters.cdi_guest | IP address of the CDI Management Software (guest OS) | 172.18.195.205 |  |  |
|  | extra_parameters.cdi_guest_user | User of the CDI Management Software (guest OS) | cdiadmin |  |  |
|  | extra_parameters.cdi_guest_password | Password of the CDI Management Software (guest OS) | *** |  |  |

### 7. TCdiBox (PCI-BOX Info)

Table name: `t_cdi_box`

| id | Column | Meaning | Example | Setting Value | Location in main.go |
|---|---|---|---|---|---|
| 1 | boxIPAddress | Management IP address for PCI-Box | 172.18.22.222 |  |  |
|  | cdi_id | ID of the connected CDI | 1 | No change needed | Inside box := &amp;model.TCdiBox{}. Specify as a variable (such as rc.CdiID) |

### 8. TCdiGpu (CDI GPU)

Describe for the number of GPUs installed in the CDI PCI-BOX

Table name: `t_cdi_gpu`

| id | Column | Meaning | Example | Setting Value | Location in main.go |
|---|---|---|---|---|---|
| 1 | ResUUID | res_uuid in CDI | f2543f10-... |  | Inside cgpuList := []*model.TCdiGpu{}.<br>Describe as a list. |
|  | ResName | Resource name in CDI | gpu0 |  |  |
|  | cdi_id | ID of the connected CDI | 1 |  | Specify as a variable (such as rc.CdiID) |
|  | box_id | ID of the installed PCI-Box | 1 |  | Specify as a variable (such as rc.ID) |
|  | UUID | GPU UUID (Note: confirm with nvidia-smi)<br>Note: A dummy value is acceptable during system construction | GPU-xxxx |  |  |
| 2 | ResUUID | res_uuid in CDI | caf49b8d-... |  |  |
|  | ResName | Resource name in CDI | gpu1 |  |  |
|  | cdi_id | ID of the connected CDI | 1 |  | Specify as a variable (such as rc.CdiID) |
|  | box_id | ID of the installed PCI-Box | 1 |  | Specify as a variable (such as rc.ID) |
|  | UUID | GPU UUID (Note: confirm with nvidia-smi)<br>Note: A dummy value is acceptable during system construction | GPU-xxxx |  |  |
| 3 | ResUUID | res_uuid in CDI | caf49b80-... |  |  |
|  | ResName | Resource name in CDI | gpu3 |  |  |
|  | cdi_id | ID of the connected CDI | 1 |  | Specify as a variable (such as rc.CdiID) |
|  | box_id | ID of the installed PCI-Box | 1 |  | Specify as a variable (such as rc.ID) |
|  | UUID | GPU UUID (Note: confirm with nvidia-smi)<br>Note: A dummy value is acceptable during system construction | GPU-xxxx |  |  |

(Continue in the same way for as many entries as needed)

### 9. TCdiSsd (CDI SSD)

Describe for the number of SSDs installed in the CDI PCI-BOX

Table name: `t_cdi_ssd`

| id | Column | Meaning | Example | Setting Value | Location in main.go |
|---|---|---|---|---|---|
| 1 | ResUUID | res_uuid in CDI | f2543f20-... |  | Inside cssdList := []*model.TCdiSsd{}.<br>Describe as a list. |
|  | ResName | Resource name in CDI | ssd0 |  |  |
|  | cdi_id | ID of the connected CDI | 1 |  | Specify as a variable (such as rc.CdiID) |
|  | box_id | ID of the installed PCI-Box | 1 |  | Specify as a variable (such as rc.ID) |
|  | StorageGb | Capacity (GB) | 960 |  |  |
| 2 | ResUUID | res_uuid in CDI | f2543f80-... |  |  |
|  | ResName | Resource name in CDI | ssd1 |  |  |
|  | cdi_id | ID of the connected CDI | 1 |  | Specify as a variable (such as rc.CdiID) |
|  | box_id | ID of the installed PCI-Box | 1 |  | Specify as a variable (such as rc.ID) |
|  | StorageGb | Capacity (GB) | 960 |  |  |

(Continue in the same way for as many entries as needed)

### 10. TCdiComputePool (CDI Compute)

Describe for the number of CDI Compute Servers

Table name: `t_cdi_compute_pool`

| server_id | Column | Meaning | Example | Setting Value | Location in main.go |
|---|---|---|---|---|---|
| 1 | HostName | Hostname (unique name) | pgcdi-compute01 |  | Inside ccpList := []*model.TCdiComputePool{}.<br>Describe as a list. |
|  | IpmiAddress | IPMI/BMC IP address | 172.18.111.222 |  |  |
|  | IpmiUser | IPMI User | user1 |  |  |
|  | IpmiPassword | IPMI Password | ** |  |  |
|  | MgrMacAddress | MAC address of Manager NIC | f0:b2... |  |  |
|  | HostMacAddress | MAC address of Host NIC | f0:b2... |  |  |
|  | CniMacAddress | MAC address of CNI NIC | b8:3f... |  |  |
|  | ApldataMacAddress | MAC address of Application Data NIC | 94:6d... |  | Specify the pointer of the variable |
|  | HostNwPortID | Column to set the switch port to which the Host NW NIC is connected. Among the records registered in the t_nw_port table, set the value of the primary key (id) of the record whose switch and port correspond.<br> Note 1: The primary key (id) of the t_nw_port table is a sequential number starting from 1 and is automatically assigned when the record is registered. | 1 |  |  |
|  | CniNwPortID | Column to set the switch port to which the CNI NW NIC is connected. Among the records registered in the t_nw_port table, set the value of the primary key (id) of the record whose switch and port correspond.<br> Note 1: The primary key (id) of the t_nw_port table is a sequential number starting from 1 and is automatically assigned when the record is registered. | 2 |  |  |
|  | ApldataNwPortID | When the Compute Server is equipped with an Application Data NIC, column to set the switch port to which the Application Data NW NIC is connected. As with the Host NW, set the value of the primary key (id) of the record whose switch and port correspond.<br> Note 1: The primary key (id) of the t_nw_port table is a sequential number starting from 1 and is automatically assigned when the record is registered. | 3 |  | Specify the pointer of the variable |
|  | ApldataNicModel | Application Data NIC model | NVIDIA-CONNECTX-6-DX |  | Specify the pointer of the variable |
|  | CPUCores | Number of CPU cores | 144 |  |  |
|  | Memory | Memory size (MiB) | 533504 |  |  |
|  | cdi_id | Specify the ID of the connected CDI as a variable (such as rc.CdiID) | 1 |  |  |
|  | ResName | Resource name in CDI | pcpu0 |  |  |
|  | product_info.vendor | Vendor | fujitsu |  |  |
|  | product_info.product_name | Product name | PRIMERGY RX2530 M7 |  |  |
|  | product_info.version | Version | none |  |  |
| 2 | HostName | Hostname (unique name) | pgcdi-compute01 |  | Inside ccpList := []*model.TCdiComputePool{}.<br>Describe as a list. |
|  | IpmiAddress | IPMI/BMC IP address | 172.18.111.222 |  |  |
|  | IpmiUser | IPMI User | user1 |  |  |
|  | IpmiPassword | IPMI Password | ** |  |  |
|  | MgrMacAddress | MAC address of Manager NIC | f0:b2... |  |  |
|  | HostMacAddress | MAC address of Host NIC | f0:b2... |  |  |
|  | CniMacAddress | MAC address of CNI NIC | b8:3f... |  |  |
|  | ApldataMacAddress | MAC address of Application Data NIC | 94:6d... |  | Specify the pointer of the variable |
|  | HostNwPortID | Column to set the switch port to which the Host NW NIC is connected. Among the records registered in the t_nw_port table, set the value of the primary key (id) of the record whose switch and port correspond.<br> Note 1: The primary key (id) of the t_nw_port table is a sequential number starting from 1 and is automatically assigned when the record is registered. | 1 |  |  |
|  | CniNwPortID | Column to set the switch port to which the CNI NW NIC is connected. Among the records registered in the t_nw_port table, set the value of the primary key (id) of the record whose switch and port correspond.<br> Note 1: The primary key (id) of the t_nw_port table is a sequential number starting from 1 and is automatically assigned when the record is registered. | 2 |  |  |
|  | ApldataNwPortID | When the Compute Server is equipped with an Application Data NIC, column to set the switch port to which the Application Data NW NIC is connected. As with the Host NW, set the value of the primary key (id) of the record whose switch and port correspond.<br> Note 1: The primary key (id) of the t_nw_port table is a sequential number starting from 1 and is automatically assigned when the record is registered. | 3 |  | Specify the pointer of the variable |
|  | ApldataNicModel | Application Data NIC model | NVIDIA-CONNECTX-6-DX |  | Specify the pointer of the variable |
|  | CPUCores | Number of CPU cores | 144 |  |  |
|  | Memory | Memory size (MiB) | 533504 |  |  |
|  | cdi_id | Specify the ID of the connected CDI as a variable (such as rc.CdiID) | 1 |  |  |
|  | ResName | Resource name in CDI | pcpu0 |  |  |
|  | product_info.vendor | Vendor | fujitsu |  |  |
|  | product_info.product_name | Product name | PRIMERGY RX2530 M7 |  |  |
|  | product_info.version | Version | none |  |  |

(Continue in the same way for as many entries as needed)

### 11. TCotsServerPool (COTS Server)

Describe for the number of COTS Servers

Table name: `t_cots_server_pool`

| server_id | Column | Meaning | Example | Setting Value | Location in main.go |
|---|---|---|---|---|---|
| 1 | Location | Location | dc1 | dc1 | Inside cotsList := []*model.TCotsServerPool{}.<br>Describe as a list.<br>Note: Location here is a string. |
|  | HostName | Hostname (unique name) | cots-control01 |  |  |
|  | IpmiAddress | IPMI/BMC address | 172.18.111.61 |  |  |
|  | IpmiUser | IPMI User | user1 |  |  |
|  | IpmiPassword | IPMI Password | ** |  |  |
|  | ServerRole | 0: K8s Control Plane, 1: K8s Worker Node | 0 | 0 | For Control Plane |
|  | DeploymentType | 0: VM host, 1: bare metal | 1 | 1 |  |
|  | MgrMacAddress | MAC address of Manager NIC | 00:00:00:00:00:01 |  |  |
|  | HostMacAddress | MAC address of Host NIC | 00:00:00:00:00:02 |  |  |
|  | HostNwPortID | Column to set the switch port to which the Host NW NIC is connected. Among the records registered in the t_nw_port table, set the value of the primary key (id) of the record whose switch and port correspond.<br> Note 1: The primary key (id) of the t_nw_port table is a sequential number starting from 1 and is automatically assigned when the record is registered. | 10 |  |  |
|  | CniMacAddress | MAC address of CNI NIC | 00:00:00:00:00:03 |  |  |
|  | CniNwPortID | Column to set the switch port to which the CNI NW NIC is connected. Among the records registered in the t_nw_port table, set the value of the primary key (id) of the record whose switch and port correspond.<br> Note 1: The primary key (id) of the t_nw_port table is a sequential number starting from 1 and is automatically assigned when the record is registered. | 11 |  |  |
|  | CPUCores | Number of CPU cores | 48 |  |  |
|  | Memory | Memory size (MiB) | 196608 |  |  |
|  | StorageGb | Storage size (GB) | 480 |  |  |
|  | product_info.vendor | Vendor | dell |  |  |
|  | product_info.product_name | Product | PowerEdge R740 |  |  |
|  | product_info.version | Version | none |  |  |
| 2 | Location | Location | dc2 | dc1 |  |
|  | HostName | Hostname (unique name) | cots-worker01 |  |  |
|  | IpmiAddress | IPMI/BMC address | 172.18.111.61 |  |  |
|  | IpmiUser | IPMI User | user1 |  |  |
|  | IpmiPassword | IPMI Password | ** |  |  |
|  | ServerRole | 0: K8s Control Plane, 1: K8s Worker Node | 1 | 0 | For Control Plane |
|  | DeploymentType | 0: VM host, 1: bare metal | 0: VM host, 1: bare metal | 1 |  |
|  | MgrMacAddress | MAC address of Manager NIC | 00:00:00:00:00:01 |  |  |
|  | HostMacAddress | MAC address of Host NIC | 00:00:00:00:00:02 |  |  |
|  | HostNwPortID | Column to set the switch port to which the Host NW NIC is connected. Among the records registered in the t_nw_port table, set the value of the primary key (id) of the record whose switch and port correspond.<br> Note 1: The primary key (id) of the t_nw_port table is a sequential number starting from 1 and is automatically assigned when the record is registered. | 5 |  |  |
|  | CniMacAddress | MAC address of CNI NIC | 00:00:00:00:00:03 |  |  |
|  | CniNwPortID | Column to set the switch port to which the CNI NW NIC is connected. Among the records registered in the t_nw_port table, set the value of the primary key (id) of the record whose switch and port correspond.<br> Note 1: The primary key (id) of the t_nw_port table is a sequential number starting from 1 and is automatically assigned when the record is registered. | 6 |  |  |
|  | CPUCores | Number of CPU cores | 128 |  |  |
|  | Memory | Memory size (MiB) | 786432 |  |  |
|  | StorageGb | Storage size (GB) | 8642 |  |  |
|  | product_info.vendor | Vendor | supermicro |  |  |
|  | product_info.product_name | Product | SYS-421GE-TNRT |  |  |
|  | product_info.version | Version | none |  |  |
| 3 | Location | Location | dc2 | dc1 |  |
|  | HostName | Hostname (unique name) | cots-worker01 |  |  |
|  | IpmiAddress | IPMI/BMC address | 172.18.111.61 |  |  |
|  | IpmiUser | IPMI User | user1 |  |  |
|  | IpmiPassword | IPMI Password | ** |  |  |
|  | ServerRole | 0: K8s Control Plane, 1: K8s Worker Node | 1 | 0 | For Control Plane |
|  | DeploymentType | 0: VM host, 1: bare metal | 1 | 1 |  |
|  | MgrMacAddress | MAC address of Manager NIC | 00:00:00:00:00:01 |  |  |
|  | HostMacAddress | MAC address of Host NIC | 00:00:00:00:00:02 |  |  |
|  | HostNwPortID | Column to set the switch port to which the Host NW NIC is connected. Among the records registered in the t_nw_port table, set the value of the primary key (id) of the record whose switch and port correspond.<br> Note 1: The primary key (id) of the t_nw_port table is a sequential number starting from 1 and is automatically assigned when the record is registered. | 9 |  |  |
|  | CniMacAddress | MAC address of CNI NIC | 00:00:00:00:00:03 |  |  |
|  | CniNwPortID | Column to set the switch port to which the CNI NW NIC is connected. Among the records registered in the t_nw_port table, set the value of the primary key (id) of the record whose switch and port correspond.<br> Note 1: The primary key (id) of the t_nw_port table is a sequential number starting from 1 and is automatically assigned when the record is registered. | 10 |  |  |
|  | CPUCores | Number of CPU cores | 128 | 64 |  |
|  | Memory | Memory size (MiB) | 786432 | 524288 |  |
|  | StorageGb | Storage size (GB) | 8642 | 960 |  |
|  | product_info.vendor | Vendor | supermicro | supermicro |  |
|  | product_info.product_name | Product | SYS-421GE-TNRT | SYS-420GP-TNR |  |
|  | product_info.version | Version | none | 123456789 |  |
| 4 | Location | Location | dc2 |  |  |
|  | HostName | Hostname (unique name) | cots-worker01 |  |  |
|  | IpmiAddress | IPMI/BMC address | 172.18.111.61 |  |  |
|  | IpmiUser | IPMI User | user1 |  |  |
|  | IpmiPassword | IPMI Password | ** |  |  |
|  | ServerRole | 0: K8s Control Plane, 1: K8s Worker Node | 1 | 1 | For Worker node |
|  | DeploymentType | 0: VM host, 1: bare metal | 1 | 1 |  |
|  | MgrMacAddress | MAC address of Manager NIC | 00:00:00:00:00:01 |  |  |
|  | HostMacAddress | MAC address of Host NIC | 00:00:00:00:00:02 |  |  |
|  | HostNwPortID | Column to set the switch port to which the Host NW NIC is connected. Among the records registered in the t_nw_port table, set the value of the primary key (id) of the record whose switch and port correspond.<br> Note 1: The primary key (id) of the t_nw_port table is a sequential number starting from 1 and is automatically assigned when the record is registered. | 9 |  |  |
|  | CniMacAddress | MAC address of CNI NIC | 00:00:00:00:00:03 |  |  |
|  | CniNwPortID | Column to set the switch port to which the CNI NW NIC is connected. Among the records registered in the t_nw_port table, set the value of the primary key (id) of the record whose switch and port correspond.<br> Note 1: The primary key (id) of the t_nw_port table is a sequential number starting from 1 and is automatically assigned when the record is registered. | 10 |  |  |
|  | ApldataMacAddress | MAC address of Application Data NIC | 00:00:00:00:00:03 |  | Specify the pointer of the variable |
|  | ApldataNwPortID | When the Compute Server is equipped with an Application Data NIC, column to set the switch port to which the Application Data NW NIC is connected. As with the Host NW, set the value of the primary key (id) of the record whose switch and port correspond.<br> Note 1: The primary key (id) of the t_nw_port table is a sequential number starting from 1 and is automatically assigned when the record is registered. | 6 |  | Specify the pointer of the variable |
|  | ApldataNicModel | Model of the Application Data NIC | NVIDIA-CONNECTX-6-DX |  | Specify the pointer of the variable |
|  | CPUCores | Number of CPU cores | 128 |  |  |
|  | Memory | Memory size (MiB) | 786432 |  |  |
|  | StorageGb | Storage size (GB) | 8642 |  |  |
|  | product_info.vendor | Vendor | supermicro |  |  |
|  | product_info.product_name | Product | SYS-421GE-TNRT |  |  |
|  | product_info.version | Version | none |  |  |

(Continue in the same way for as many entries as needed)

Association of worker id and hostname

| No | worker id | Hostname |  | Setting | Location in main.go |
|---|---|---|---|---|---|
| 1 | worker ID (such as worker1) | Hostname (such as hostname-xxx) |  |  | worker1, _ := qcots.WithContext(ctx).Where(qcots.HostName.Eq("hostname-xxx")).First() |
| 2 | worker ID (such as worker2) | Hostname (such as hostname-yyy) |  |  | worker2, _ := qcots.WithContext(ctx).Where(qcots.HostName.Eq("hostname-yyy")).First() |
| 3 | worker ID (such as worker3) | Hostname (such as hostname-zzz) |  |  | worker3, _ := qcots.WithContext(ctx).Where(qcots.HostName.Eq("hostname-zzz")).First() |

### 12. TCotsServerGpu (COTS GPU)

Describe the information of the GPUs installed in each COTS Server

Table name: `t_cots_server_gpu`

| id | Column | Meaning | Example | Setting Value | Location in main.go |
|---|---|---|---|---|---|
| 1 | server_id | server Id of t_cots_server_pool | worker1 | worker1.ServerID | Inside cotsGpuList := []*model.TCotsServerGpu{}.<br>Describe as a list.<br>Specify the ID associated with the corresponding hostname as a variable (such as worker1.ServerID) |
|  | UUID | GPU UUID (Note: confirm with nvidia-smi). A dummy value is acceptable during tenant construction. | GPU-00000000-0000-0000-0000-000000000001 |  |  |
|  | model | GPU model | NVIDIA-H100 |  |  |
| 2 | server_id | server Id of t_cots_server_pool | worker2 |  | Specify the ID associated with the corresponding hostname as a variable (such as worker1.ServerID) |
|  | UUID | GPU UUID (Note: confirm with nvidia-smi). A dummy value is acceptable during tenant construction. | GPU-00000000-0000-0000-0000-000000000001 |  |  |
|  | model | GPU model | NVIDIA-H100 |  |  |
| 3 | server_id | server Id of t_cots_server_pool | worker3 |  | Specify the ID associated with the corresponding hostname as a variable (such as worker2.ServerID) |
|  | UUID | GPU UUID (Note: confirm with nvidia-smi). A dummy value is acceptable during tenant construction. | GPU-00000000-0000-0000-0000-000000000002 |  |  |
|  | model | GPU model | NVIDIA-H100 |  |  |

(Continue in the same way for as many entries as needed)

### 13. TOsInfo (OS Info)

Describe the OS registered as an image in MAAS to be deployed to the tenant server (basically no change needed)

Table name: `t_os_info`

| id | Column | Meaning | Example | Setting Value | Location in main.go |
|---|---|---|---|---|---|
| 1 | OsDistribution | OS type | rhel | rhel | Inside osInfo := &amp;model.TOsInfo{}. |
|  | OsVersion | Version | 9.6-custom | 9.6-custom |  |
|  | LoginUser | Login User | cloud-user | cloud-user |  |

## 4. Tenant Logical Infrastructure Construction Info

Information required for tenant construction (for DCI Operator)

### 1. Cluster

Usable as-is

| Item | Example | Setting Value |
|---|---|---|
| name | tenant-1 |  |
| namespace | tenant-1 |  |
| clusterNetwork.services | 10.96.0.0/12 |  |
| clusterNetwork.pods | 10.245.0.0/16 |  |
| controlPlaneRef.kind | KubeadmControlPlane |  |
| controlPlaneRef.name | (Match the KubeadmControlPlane name) |  |
| infrastructureRef.kind | DCICluster |  |
| infrastructureRef.name | (Match the DCICluster name) |  |

### 2. DCICluster

| Column | Example | Setting Value |
|---|---|---|
| name | (Match the Cluster name) |  |
| namespace | (Match the Cluster namespace) |  |

#### controlPlaneEndpoint

Describe the VIP address used by the Control Plane of the DCI Tenant Logical Infrastructure

| Item | Example | Setting Value |
|---|---|---|
| host | 172.18.165.30 |  |
| port | 6443 |  |

#### logicalNetwork

##### manager

Describe the CIDR, VLAN ID, and usable IP address range of the Manager NW of the DCI Tenant Logical Infrastructure

| Item | Example | Setting Value |
|---|---|---|
| cidrBlock | 172.18.193.0/24 |  |
| vlanID | 1193 |  |
| ipAddressRange.start | 172.18.193.70 |  |
| ipAddressRange.end | 172.18.193.78 |  |

##### host

Describe the CIDR, VLAN ID, and usable IP address range of the Host NW of the DCI Tenant Logical Infrastructure

| Item | Example | Setting Value |
|---|---|---|
| cidrBlock | 172.18.162.0/24 |  |
| vlanID | 1162 |  |
| ipAddressRange.start | 172.18.162.10 |  |
| ipAddressRange.end | 172.18.162.200 |  |

##### cni

Describe the CIDR, VLAN ID, and usable IP address range of the CNI NW of the DCI Tenant Logical Infrastructure

| Item | Example | Setting Value |
|---|---|---|
| cidrBlock | 172.18.165.0/24 |  |
| vlanID | 1165 |  |
| ipAddressRange.start | 172.18.165.10 |  |
| ipAddressRange.end | 172.18.165.200 |  |

##### appData

Describe the CIDR, VLAN ID, and usable IP address range of the Application Data NW of the DCI Tenant Logical Infrastructure

| Item | Example | Setting Value |
|---|---|---|
| cidrBlock | 172.18.168.0/24 |  |
| vlanID | 1168 |  |
| ipAddressRange.start | 172.18.168.10 |  |
| ipAddressRange.end | 172.18.168.200 |  |

### 3. KubeadmControlPlane

Describe the information used for the Control Plane of the DCI Tenant Logical Infrastructure

| Item | Example | Setting Value | Notes |
|---|---|---|---|
| name | controlplane |  |  |
| namespace | (Match the Cluster namespace) |  |  |
| replicas | 3 |  |  |
| k8s version | v1.34.2 (match the materials used) |  |  |
| machineTemplate.spec.infrastructureRef.kind | DCIMachineTemplate |  |  |
| machineTemplate.spec.infrastructureRef.name | (Match the DCIMachineTemplate) |  |  |
| kubeadmConfigSpec.ntp.servers | 172.18.197.80 |  |  |
| files: kind.pod, spec.containers.env.vip_address | &lt;Set the same value as the controlPlaneEndpoint of DCICluster&gt; Example: 172.18.165.30 |  |  |
| preKubeadmCommands: CNI_GW | &lt;CNI NW GW IP address&gt; Example: 172.18.165.251 |  |  |
| preKubeadmCommands: nameserver | &lt;DNS IP address&gt; Example: 8.8.8.8 8.8.4.4 |  |  |
| preKubeadmCommands: KUBERNETES_VERSION | v1.34 |  |  |
| preKubeadmCommands: CRIO_VERSION | v1.34 |  |  |
| preKubeadmCommands:PODS_CIDR | &lt;CIDR used by Pod&gt; Example: 10.245.0.0/16 |  |  |
| preKubeadmCommands:MANAGER_CIDR | &lt;CIDR used by Manager NW&gt; Example: 172.18.193.0/24 |  |  |
| preKubeadmCommands:HOST_CIDR | &lt;CIDR used by Host NW&gt; Example: 172.18.162.0/24 |  |  |
| preKubeadmCommands:CNI_CIDR | &lt;CIDR used by CNI NW&gt; Example: 172.18.165.0/24 |  |  |
| TENANT_OPERATOR_CIDR | CIDR of the Tenant Operator operation terminal (required for FW connection permission) |  | <- From Address_Account_Info |
| BASTION_IP | Bastion IP address when the Tenant Operator accesses via a bastion |  | <- From Address_Account_Info |
| LB_VIP | VIP for tenant LB |  | <- From Address_Account_Info (numbered for tenant) |
| POD_CIDR | Pod CIDR for tenant |  |  |
| preKubeadmCommands:HOST_GW | &lt;Host NW GW IP address&gt; Example: 172.18.162.251 |  |  |
| RHEL activation-key | xxxxxxx |  |  |
| RHEL organization | 12345678 |  |  |
| kubernetes package name | (package name of k8s to install) |  |  |
| CRI-O package name | (package name of cri-o to install) |  |  |

### 4. KubeadmConfigTemplate

Describe the information used for the worker node of the DCI Tenant Logical Infrastructure

| Item | Example | Setting Value | Notes |
|---|---|---|---|
| name | worker |  |  |
| namespace | (Match the Cluster namespace) |  |  |
| ntp.servers | 172.18.197.80 |  |  |
| preKubeadmCommands: PODS_CIDR | &lt;CIDR used by Pod&gt; Example: 10.245.0.0/16 |  |  |
| preKubeadmCommands: SVC_CIDR | &lt;CIDR used by service&gt; Example: 10.96.0.0/12 |  |  |
| preKubeadmCommands: MANAGER_CIDR | &lt;CIDR used by Manager NW&gt; Example: 172.18.193.0/24 |  |  |
| preKubeadmCommands: HOST_CIDR | &lt;CIDR used by Host NW&gt; Example: 172.18.162.0/24 |  |  |
| preKubeadmCommands: CNI_CIDR | &lt;CIDR used by CNI NW&gt; Example: 172.18.165.0/24 |  |  |
| preKubeadmCommands: nameserver | 8.8.8.8 8.8.4.4 |  |  |
| preKubeadmCommands: CNI_GW | &lt;CNI NW GW IP address&gt; Example: 172.18.165.251 |  |  |
| preKubeadmCommands: HOST_GW | &lt;Host NW GW IP address&gt; Example: 172.18.162.251 |  |  |
| TENANT_OPERATOR_CIDR | CIDR of the Tenant Operator operation terminal (required for FW connection permission) |  | <- From Address_Account_Info |
| BASTION_IP | Bastion IP address when the Tenant Operator accesses via a bastion |  | <- From Address_Account_Info |
| POD_CIDR | Pod CIDR for tenant |  |  |
| RHEL activation-key | XXXXXXXXX |  |  |
| RHEL organization | 12345678 |  |  |

### 5. DCIMachineTemplate (controlplane)

Describe the machine information used by the Control Plane of the DCI Tenant Logical Infrastructure

| Item | Example | Setting Value |
|---|---|---|
| name | controlplane |  |
| namespace | (Match the Cluster namespace) |  |
| location | (Match the Location of the Configuration Management DB) |  |
| serverSpec.type | VM (fixed) |  |
| os.distribution | rhel (fixed) |  |
| os.version | 9.6-custom (fixed) |  |
| minCPU | 4 |  |
| minMemory(MiB) | 32768 |  |
| minStorage(GB) | 80 |  |

### 6. DCIMachineTemplate (worker node1)

Describe the machine information used by worker node1 of the DCI Tenant Logical Infrastructure

| Item | Example | Setting Value |
|---|---|---|
| name | worker-1 |  |
| namespace | (Match the Cluster namespace) |  |
| location | (Match the Location of the Configuration Management DB) |  |
| serverSpec.type | COTSServer |  |
| os.distribution | rhel (fixed) |  |
| os.version | 9.6-custom (fixed) |  |
| gpu.model | NVIDIA-BLACKWELL |  |
| gpu.num | 2 |  |
| nic.model | NVIDIA-CONNECTX-6-DX |  |
| nic.num | 1 |  |

### 7. DCIMachineTemplate (worker node2)

*Note: If necessary*

Describe the machine information used by worker node2 of the DCI Tenant Logical Infrastructure

| Item | Example | Setting Value |
|---|---|---|
| name | worker-2 |  |
| namespace | (Match the Cluster namespace) |  |
| location | (Match the Location of the Configuration Management DB) |  |
| serverSpec.type | ComposedServer (fixed) |  |
| os.distribution | rhel (fixed) |  |
| os.version | 9.6-custom (fixed) |  |
| gpu.model | NVIDIA-H100-PCIE-80GB |  |
| gpu.num | 1 |  |
| nic.model | NVIDIA-CONNECTX-6-DX |  |
| nic.num | 1 |  |

### 8. MachineDeployment (worker-md-1)

Describe the information used for worker node1 of the DCI Tenant Logical Infrastructure

| Item | Example | Setting Value |
|---|---|---|
| name | worker-md-1 |  |
| namespace | (Match the Cluster namespace) |  |
| clusterName | (Match the Cluster name) |  |
| replicas | 1 |  |
| selector.matchLabels.cluster.x-k8s.io/cluster-name | Set the same as clusterName |  |
| version | v1.34.2 (match the materials used) |  |
| infrastructureRef.kind | DCIMachineTemplate |  |
| infrastructureRef.name | worker-1 |  |

### 9. MachineDeployment (worker-md-2)

*Note: If necessary*

Describe the information used for worker node2 of the DCI Tenant Logical Infrastructure

| Item | Example | Setting Value |
|---|---|---|
| name | worker-md-2 |  |
| namespace | (Match the Cluster namespace) |  |
| clusterName | (Match the Cluster name) |  |
| replicas | 1 |  |
| version | v1.34.2 (match the materials used) |  |
| infrastructureRef.kind | DCIMachineTemplate |  |
| infrastructureRef.name | worker-2 |  |

Copyright 2026 NTT, Inc.
