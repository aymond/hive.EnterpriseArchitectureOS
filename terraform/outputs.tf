output "instance_public_ip" {
  description = "The public IP address of the deployed OCI instance."
  value       = oci_core_instance.ea_os_instance.public_ip
}

output "ssh_command" {
  description = "The command to SSH into the newly created instance."
  value       = "ssh ubuntu@${oci_core_instance.ea_os_instance.public_ip}"
}
