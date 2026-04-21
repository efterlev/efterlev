# aws.tls_on_lb_listeners

Detects whether AWS load balancer listeners (`aws_lb_listener`,
`aws_alb_listener`) accept connections over TLS/HTTPS rather than plain
HTTP/TCP.

## What this proves

- **KSI-SVC-SNT (Securing Network Traffic), partial.** The listener's
  Terraform configuration declares HTTPS or TLS as its accept protocol.
- **NIST SP 800-53 SC-8 (Transmission Confidentiality and Integrity),
  partial.** Infrastructure-layer evidence only — the listener will not
  accept plaintext traffic in its declared configuration.

## What this does NOT prove

- Whether an HTTP listener on the same load balancer redirects to the
  HTTPS listener. If an HTTP listener exists alongside HTTPS without a
  redirect rule, traffic can still flow unencrypted.
- Whether the listener's `ssl_policy` is FIPS-compliant. A separate
  detector (v1) evaluates cipher-suite choices. HTTPS with a weak
  policy still counts as "present" here.
- Certificate validity, rotation, or hostname binding. Those are
  runtime concerns the scanner cannot see from Terraform source alone.
- Whether the certificate referenced by `certificate_arn` exists or is
  trusted by clients.

## Evidence shape

See `evidence.yaml`. Each listener resource produces one Evidence
record with `tls_state ∈ {present, absent, unknown}`. "Unknown" is
emitted when the `protocol` attribute is missing or unrecognized —
the Gap Agent treats this as partial rather than false-positive
implemented.
