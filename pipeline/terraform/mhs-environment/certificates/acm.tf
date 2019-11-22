resource "aws_acm_certificate" "mhs-inbound" {
  private_key      = "${file("${path.module}/mhs-certs/mhs-inbound.key")}"
  certificate_body = "${file("${path.module}/mhs-certs/mhs-inbound.crt")}"
  certificate_chain = "${file("${path.module}/mhs-certs/mhs-inbound-combined.crt")}"
}

resource "aws_acm_certificate" "mhs-route" {
  private_key      = "${file("${path.module}/mhs-certs/mhs-route.key")}"
  certificate_body = "${file("${path.module}/mhs-certs/mhs-route.crt")}"
  certificate_chain = "${file("${path.module}/mhs-certs/mhs-route-combined.crt")}"
}

resource "aws_acm_certificate" "mhs-outbound" {
  private_key      = "${file("${path.module}/mhs-certs/mhs-outbound.key")}"
  certificate_body = "${file("${path.module}/mhs-certs/mhs-outbound.crt")}"
  certificate_chain = "${file("${path.module}/mhs-certs/mhs-outbound-combined.crt")}"
}

output "mhs-inbound" {
  value = aws_acm_certificate.mhs-inbound.arn
}

output "mhs-route" {
  value = aws_acm_certificate.mhs-route.arn
}

output "mhs-outbound" {
  value = aws_acm_certificate.mhs-outbound.arn
}
