# DCI-2.0 Checklist (Before DCI Management Cluster Construction)

Checklist for the DCI Operator before constructing the DCI Management Cluster.

Check each box after verifying the corresponding item.

## Operation Terminal

### For DCI Operator

- [ ] Is the terminal (RHEL recommended) operated by the DCI Operator prepared?

## DCI Management Server

### BIOS

- [ ] **System Board**: Are there no hardware errors (CPU, PCI bus errors, etc.)?
- [ ] **IPMI/BMC**: Are the IPMI IP address and GW configured?

### OS

- [ ] **RHEL9.6**: Installed on the DCI Management Server and RHEL subscription registered?
  - For Control Plane x3 units
  - For k8s node x2 units
  - For MAAS server x1 unit

### Service

- [ ] **firewalld**: Is the firewalld service stopped?
- [ ] **DNS**: Is the DNS server available? (Name resolution / external access possible?)
- [ ] **NTP**: Is the NTP server available? (Time synchronization configurable?)

## PG-CDI

### CDI Device

- [ ] **System Construction**: Are the CDI devices connected and setup completed?
  - Management Server
  - CDI Management Software
  - Director
  - Fabric SW+, PCI-BOX
  - Compute Server
  - CDI Client PC

### CDI Management Software

- [ ] **Configuration Verification**: Is the CDI Management Software (Guest OS) started?
- [ ] **Configuration Verification**: Does the hhchk.cfg file exist in the cdiadmin home directory of the CDI Management Software (Guest OS)?

### Linux Client PC

- [ ] **Configuration Verification**: Is the VM created and the client PC running?
- [ ] **Configuration Verification**: Is expect installed?
- [ ] **Configuration Verification**: Is the cdictl Path configured (symbolic link)?
- [ ] **Configuration Verification**: Is resource group0 configured with cdictl?
- [ ] **Configuration Verification**: Is the user dhrcsystem for the DHRC component created?

## NW Device

### SW General

- [ ] **Management Port**: Are the IP address and GW configured?

### L2 SW

- [ ] **For HOST, For CNI, For APPDATA**: Are the ports targeted for operation from DHRC free of VLAN configuration (including the default VLAN)? (Are VLANs removed?)
- [ ] **For HOST, For CNI, For APPDATA**: Is LLDP enabled on the connected ports?

### L3 SW

- [ ] **Between Manager and Tenant**: Is ACL/VLAN routing configured?
- [ ] **Between Tenant and Tenant**: Is routing not configured between VLANs of different tenants (NW isolated)?

## MAAS

### MAAS3.6.x

- [ ] **Server**: Is the MAAS server constructed and the MAAS GUI accessible?
- [ ] **OS image**: Is the RHEL9.6 OS custom image registered in MAAS?
- [ ] **DHCP**: Is the Manager NW (NIC1) Subnet configured / DHCP enabled, and fixed addresses configured with static DHCP leases?
- [ ] **DHCP**: For dynamic IP address assignment, is the DHCP Dynamic reserved range configured?
- [ ] **DHCP**: Is the free pool for VMs configured (excluded from the DHCP reserved range)?

## DCI Tenant Logical Infrastructure Resources

### COTS Server

- [ ] **IPMI/BMC (configured via GUI such as iDRAC / iRMC)**: Is IPMI over LAN enabled?

### Composed Server

- [ ] **IPMI/BMC (configured via GUI such as iDRAC / iRMC)**: Is redfish enabled?
- [ ] **BIOS Settings**: Is PXEboot enabled on the Manager NIC?
- [ ] **BIOS Settings**: Boot order: Is Manager NIC1 first for PXEboot?
- [ ] **BIOS Settings**: Is SR-IOV enabled?

## Network Connectivity Verification

### Manager NW

- [ ] **IPMI/BMC NIC**: Is ping connectivity OK from the operation terminal to all set-up devices?
- [ ] **HW Management NIC**: Is ping connectivity OK from the operation terminal to all set-up devices?
- [ ] **HW Management NIC**: Is external (Internet) connection possible from the Manager NW?

## External Storage

### For PV

- [ ] **NFS**: Is the NFS server available?
- [ ] **NFS**: Is no_root_squash configured on the NFS server?

### For Backup

- [ ] **S3-compatible**: Is MinIO available as backup storage?

Copyright 2026 NTT, Inc.
