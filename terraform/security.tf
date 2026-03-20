resource "oci_core_security_list" "ea_os_sl" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.ea_os_vcn.id
  display_name   = "hive_ea_os_security_list"

  egress_security_rules {
    destination = "0.0.0.0/0"
    protocol    = "all"
  }

  ingress_security_rules {
    protocol = "6" # TCP
    source   = "0.0.0.0/0"
    tcp_options {
      max = 22
      min = 22
    }
  }

  ingress_security_rules {
    protocol = "6" # TCP
    source   = "0.0.0.0/0"
    tcp_options {
      max = 80
      min = 80
    }
  }

  ingress_security_rules {
    protocol = "6" # TCP
    source   = "0.0.0.0/0"
    tcp_options {
      max = 443
      min = 443
    }
  }
}
