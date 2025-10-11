terraform {
  required_version = ">= 1.6"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.24"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.12"
    }
  }

  backend "s3" {
    bucket         = "carpeta-ciudadana-terraform-state"
    key            = "terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-lock"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "CarpetaCiudadana"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

data "aws_eks_cluster" "cluster" {
  name = module.eks.cluster_name

  depends_on = [module.eks]
}

data "aws_eks_cluster_auth" "cluster" {
  name = module.eks.cluster_name

  depends_on = [module.eks]
}

provider "kubernetes" {
  host                   = data.aws_eks_cluster.cluster.endpoint
  cluster_ca_certificate = base64decode(data.aws_eks_cluster.cluster.certificate_authority[0].data)
  token                  = data.aws_eks_cluster_auth.cluster.token
}

provider "helm" {
  kubernetes {
    host                   = data.aws_eks_cluster.cluster.endpoint
    cluster_ca_certificate = base64decode(data.aws_eks_cluster.cluster.certificate_authority[0].data)
    token                  = data.aws_eks_cluster_auth.cluster.token
  }
}

# VPC
module "vpc" {
  source = "./modules/vpc"

  environment         = var.environment
  vpc_cidr            = var.vpc_cidr
  availability_zones  = var.availability_zones
  private_subnets     = var.private_subnets
  public_subnets      = var.public_subnets
}

# EKS
module "eks" {
  source = "./modules/eks"

  environment         = var.environment
  cluster_name        = "${var.project_name}-${var.environment}"
  cluster_version     = var.eks_cluster_version
  vpc_id              = module.vpc.vpc_id
  private_subnet_ids  = module.vpc.private_subnet_ids
  node_instance_types = var.eks_node_instance_types
  desired_size        = var.eks_desired_size
  min_size            = var.eks_min_size
  max_size            = var.eks_max_size
}

# RDS PostgreSQL
module "rds" {
  source = "./modules/rds"

  environment         = var.environment
  db_name             = "carpeta_ciudadana"
  db_username         = var.db_username
  db_instance_class   = var.db_instance_class
  allocated_storage   = var.db_allocated_storage
  vpc_id              = module.vpc.vpc_id
  private_subnet_ids  = module.vpc.private_subnet_ids
  allowed_cidr_blocks = module.vpc.private_subnet_cidrs
}

# S3
module "s3" {
  source = "./modules/s3"

  environment = var.environment
  bucket_name = "${var.project_name}-documents-${var.environment}"
}

# OpenSearch
module "opensearch" {
  source = "./modules/opensearch"

  environment        = var.environment
  domain_name        = "${var.project_name}-${var.environment}"
  instance_type      = var.opensearch_instance_type
  instance_count     = var.opensearch_instance_count
  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.private_subnet_ids
  security_group_ids = [module.vpc.default_security_group_id]
}

# Cognito
module "cognito" {
  source = "./modules/cognito"

  environment = var.environment
  pool_name   = "${var.project_name}-users-${var.environment}"
  domain      = "${var.project_name}-${var.environment}"
}

# SQS/SNS
module "messaging" {
  source = "./modules/messaging"

  environment = var.environment
  queue_name  = "${var.project_name}-events-${var.environment}"
  topic_name  = "${var.project_name}-notifications-${var.environment}"
}

# ACM Private CA
module "acm_pca" {
  source = "./modules/acm_pca"

  environment = var.environment
  ca_name     = "${var.project_name}-ca-${var.environment}"
}

# ECR
module "ecr" {
  source = "./modules/ecr"

  environment = var.environment
  repositories = [
    "frontend",
    "gateway",
    "citizen",
    "ingestion",
    "signature",
    "metadata",
    "transfer",
    "sharing",
    "notification",
    "mintic-client"
  ]
}

# IAM Roles for Services
module "iam" {
  source = "./modules/iam"

  environment      = var.environment
  eks_cluster_name = module.eks.cluster_name
  oidc_provider    = module.eks.oidc_provider
  s3_bucket_arn    = module.s3.bucket_arn
  sqs_queue_arn    = module.messaging.queue_arn
  sns_topic_arn    = module.messaging.topic_arn
}

