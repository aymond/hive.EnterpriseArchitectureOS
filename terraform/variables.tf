variable "tenancy_ocid" {
  description = "The OCID of the tenancy."
  type        = string
}

variable "user_ocid" {
  description = "The OCID of the user calling the API."
  type        = string
}

variable "private_key_path" {
  description = "The path to the private key used to authenticate with OCI."
  type        = string
}

variable "fingerprint" {
  description = "The fingerprint of the public key."
  type        = string
}

variable "region" {
  description = "The region to provision the resources in."
  type        = string
  default     = "us-ashburn-1"
}

variable "compartment_ocid" {
  description = "The OCID of the compartment to deploy resources into."
  type        = string
}

variable "ssh_public_key" {
  description = "The SSH public key to add to the compute instance."
  type        = string
}

variable "instance_shape" {
  description = "The shape of the compute instance."
  type        = string
  default     = "VM.Standard.E4.Flex"
}

variable "instance_ocpus" {
  description = "Number of OCPUs for the flex instance."
  type        = number
  default     = 1
}

variable "instance_memory_in_gbs" {
  description = "Amount of memory (in GBs) for the flex instance."
  type        = number
  default     = 8
}
