resource "oci_core_vcn" "ea_os_vcn" {
  cidr_block     = "10.0.0.0/16"
  compartment_id = var.compartment_ocid
  display_name   = "hive_ea_os_vcn"
  dns_label      = "hiveosvcn"
}

resource "oci_core_internet_gateway" "ea_os_ig" {
  compartment_id = var.compartment_ocid
  display_name   = "hive_ea_os_ig"
  vcn_id         = oci_core_vcn.ea_os_vcn.id
}

resource "oci_core_default_route_table" "ea_os_route_table" {
  manage_default_resource_id = oci_core_vcn.ea_os_vcn.default_route_table_id

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.ea_os_ig.id
  }
}

data "oci_identity_availability_domains" "ads" {
  compartment_id = var.compartment_ocid
}

resource "oci_core_subnet" "ea_os_subnet" {
  cidr_block        = "10.0.1.0/24"
  compartment_id    = var.compartment_ocid
  vcn_id            = oci_core_vcn.ea_os_vcn.id
  display_name      = "hive_ea_os_subnet"
  dns_label         = "hiveossub"
  route_table_id    = oci_core_vcn.ea_os_vcn.default_route_table_id
  security_list_ids = [oci_core_security_list.ea_os_sl.id]
}
