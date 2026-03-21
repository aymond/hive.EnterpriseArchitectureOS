# Deploying to Oracle Cloud Infrastructure (OCI)

This guide walks you through automatically provisioning an OCI Virtual Machine (Compute Instance) and deploying the `hive.EnterpriseArchitectureOS` application using our Terraform infrastructure-as-code setup.

## 🏗 What This Does

The included Terraform configuration (`/terraform` directory) will:
1. Create a **Virtual Cloud Network (VCN)** and public subnet.
2. Configure **Security Lists** to expose ports 22 (SSH), 80 (HTTP), and 443 (HTTPS) to the internet.
3. Provision an **Ubuntu Compute Instance** (defaults to `VM.Standard.E4.Flex`, but ARM-based `VM.Standard.A1.Flex` is fully supported!).
4. Automatically inject and execute `deploy.sh` as a startup script (`cloud-init`).
   *(This means the server will automatically install Docker, clone this repository, and start the containers upon first boot!)*

All published Docker images are multi-architecture (`linux/amd64`, `linux/arm64/v8`) to support both Intel/AMD and Ampere ARM platforms seamlessly.

---

## 📋 Prerequisites

Before you begin, ensure you have the following installed on your local machine:
- [Terraform](https://developer.hashicorp.com/terraform/downloads) (v1.0.0+)
- [OCI CLI](https://docs.oracle.com/en-us/iaas/Content/API/SDKDocs/cliinstall.htm) (configured with your tenancy and user OCIDs)
- An SSH Key Pair (e.g. `~/.ssh/id_rsa.pub`) to access the VM.

## 🚀 Step 1: Configure Terraform Inputs

Navigate to the `terraform` directory:
```bash
cd terraform
```

Create a file named `terraform.tfvars` inside the `terraform` directory to hold your specific OCI credentials and variables:

```hcl
# terraform/terraform.tfvars

tenancy_ocid     = "ocid1.tenancy.oc1..xxxxxx"
user_ocid        = "ocid1.user.oc1..xxxxxx"
fingerprint      = "xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx"
private_key_path = "~/.oci/oci_api_key.pem"
region           = "us-ashburn-1" # Or your preferred OCI region

# The compartment where you want these resources deployed
compartment_ocid = "ocid1.compartment.oc1..xxxxxx"

# Your public SSH key string for accessing the VM
ssh_public_key   = "ssh-rsa AAAAB3NzaC1yc... user@machine"
```

## 🚀 Step 2: Provision Infrastructure

From inside the `terraform/` directory, initialize the providers:

```bash
terraform init
```

Preview the changes:
```bash
terraform plan
```

Deploy the infrastructure. This action will create the network, security lists, and the VM:
```bash
terraform apply
```
*Note: Type `yes` when prompted to confirm the application. It will take a few minutes for the VM to start and for the `deploy.sh` script to finish running.*

At the end of the deployment, Terraform will output the **public IP address** of your new machine:
```bash
Outputs:
instance_public_ip = "123.45.67.89"
ssh_command        = "ssh ubuntu@123.45.67.89"
```

## 🚀 Step 3: Application Configuration

Even though Terraform automatically installed Docker and started the containers via `deploy.sh`, you **must** configure your API keys for the backend to function securely!

1. SSH into the newly created machine:
   ```bash
   ssh ubuntu@<your_instance_public_ip>
   ```

2. Navigate to the deployed app directory:
   ```bash
   cd /opt/hive-ea-os
   ```

3. Copy the example environment file and fill in your secrets:
   ```bash
   sudo cp .env.oci.example .env
   sudo nano .env
   ```
   **Required Secrets to populate:**
   - `OPENAI_API_KEY`: Your OpenAI key.
   - `TAVILY_API_KEY`: Your Tavily string.
   - `NEO4J_PASSWORD`: Change this to a secure database password!
   - `JWT_SECRET_KEY`: Generate a random string (e.g., `openssl rand -hex 32`).
   - `ALLOWED_ORIGINS`: Add your VM's Public IP (e.g., `http://123.45.67.89`).

4. Restart the Docker containers to pick up the new `.env` settings:
   ```bash
   sudo docker compose up -d --build
   ```

## 🎉 Step 4: Access Your Application

Once the containers restart seamlessly, your Enterprise Architecture OS is live!

Open your browser and navigate directly to your instance's public IP address over HTTP:
- **Application URL**: `http://<your_instance_public_ip>`

*Welcome to your containerized cloud OS!*
