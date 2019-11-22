#!/bin/bash

set -Eeo pipefail

CERTIFICATES_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

PKI_DIR="${CERTIFICATES_DIR}/CA"
generated_certs_dir="${CERTIFICATES_DIR}/mhs-certs/"

function mhs_prepare_certs {
  keys_file_name="$1"
  # If you intend to secure the URL https://www.yourdomain.com, then your CSR’s common name must be www.yourdomain.com
  common_name="$2"
  # ip1="10.4.0.5"
  organization_name='NHS Digital'
  fqdn=$common_name

  if [[ -z ${CA_PASSWORD} ]]; then
    echo "CA_PASSWORD is not set. Exit 1"
    exit 1
  fi
  if [[ ! -d ${PKI_DIR} ]]; then
    echo "${PKI_DIR} does not exist, exit 1"
    exit 1
  fi
  if [[  ! -f ${PKI_DIR}/certs/ca.crt ]] && [[ ! -f ${PKI_DIR}/private/ca.key ]]; then
    echo "${PKI_DIR}/certs/ca.crt and ${PKI_DIR}/private/ca.key must exist"
    exit 1
  fi
  if [[  -f "${generated_certs_dir}/${keys_file_name}.key" ]]; then
    echo "${generated_certs_dir}/${keys_file_name}.key already exist"
    return 0
  fi
  echo "Preparing certificates for: ${keys_file_name} on ${fqdn}, common_name: ${common_name}, organization_name: ${organization_name}"

  # 1. Create a config file for generating a Certificate Signing Request (CSR).
  cat <<EOF >./csr.conf
[ req ]
default_bits = 2048
prompt = no
default_md = sha256
req_extensions = req_ext
distinguished_name = dn

[ dn ]
CN = ${common_name}
O = ${organization_name}
# Organization Unit Name, let's use it as commentary
OU = Deductions Team

[ req_ext ]
subjectAltName = @alt_names

[ alt_names ]
DNS.1 = ${fqdn}

[ v3_ext ]
authorityKeyIdentifier=keyid,issuer:always
basicConstraints=CA:FALSE
keyUsage=keyEncipherment,dataEncipherment
extendedKeyUsage=serverAuth,clientAuth
subjectAltName=@alt_names
EOF

  # 2. Create a private key (${keys_file_name}.key) and then generate a certificate request (${keys_file_name}.csr) from it:
  # (steps 3. and 5. from: https://kubernetes.io/docs/concepts/cluster-administration/certificates/)
  # https://www.openssl.org/docs/manmaster/man1/req.html
  openssl genrsa -out ${keys_file_name}.key 2048
  openssl req -new -key ${keys_file_name}.key -out ${keys_file_name}.csr -config csr.conf
  # the same but with 1 line:
  # openssl req -newkey rsa:4096 -keyout ${keys_file_name}.key -out ${keys_file_name}.csr
  # 3. Generate the server certificate (${keys_file_name}.crt) using the ca.key, ca.crt and ${keys_file_name}.csr:
  openssl x509 -req -in ${keys_file_name}.csr -CA ${PKI_DIR}/certs/ca.crt -CAkey ${PKI_DIR}/private/ca.key \
    -CAcreateserial -out ${keys_file_name}.crt -days 36500 \
    -extensions v3_ext -extfile csr.conf -passin pass:${CA_PASSWORD}

  mkdir -p ${generated_certs_dir}
  cp ${PKI_DIR}/certs/ca.crt ${generated_certs_dir}/
  # see https://www.vaultproject.io/docs/configuration/listener/tcp.html#tls_cert_file
  cat ${keys_file_name}.crt ${PKI_DIR}/certs/ca.crt > ${generated_certs_dir}/${keys_file_name}-combined.crt
  mv ${keys_file_name}.crt ${generated_certs_dir}/
  mv ${keys_file_name}.key ${generated_certs_dir}/
  rm ${keys_file_name}.csr
  chmod 660 "${generated_certs_dir}/"*
  chmod 755 "${generated_certs_dir}"
}

command="$1"
case "${command}" in
  generate)
    MHS_ENVIRONMENT=local
    mhs_prepare_certs "mhs-outbound" "mhs-outbound.$MHS_ENVIRONMENT.internal-mhs.nhs.net"
    mhs_prepare_certs "mhs-inbound" "mhs-inbound.$MHS_ENVIRONMENT.internal-mhs.nhs.net"
    mhs_prepare_certs "mhs-route" "mhs-route.$MHS_ENVIRONMENT.internal-mhs.nhs.net"
    ;;
  *)
      echo "Invalid command: '${command}'"
      exit 1
      ;;
esac
set +e
