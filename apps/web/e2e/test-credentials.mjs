import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../../..');

function readCredentialFile() {
  const path = process.env.TRANSMUTER_TEST_CREDENTIALS_FILE
    ? resolve(process.env.TRANSMUTER_TEST_CREDENTIALS_FILE)
    : resolve(repoRoot, 'scratch/test-credentials.json');

  try {
    return JSON.parse(readFileSync(path, 'utf8'));
  } catch (error) {
    throw new Error(
      `Test credentials are required. Set credential environment variables or provide ${path}: ${error.message}`,
    );
  }
}

export function loadTestCredentials({
  tenant = 'acme',
  role,
  emailEnv = 'TRANSMUTER_E2E_EMAIL',
  passwordEnv = 'TRANSMUTER_E2E_PASSWORD',
} = {}) {
  const environmentEmail = process.env[emailEnv];
  const environmentPassword = process.env[passwordEnv];
  if (environmentEmail && environmentPassword) {
    return { email: environmentEmail, password: environmentPassword };
  }
  if (environmentEmail || environmentPassword) {
    throw new Error(`${emailEnv} and ${passwordEnv} must be set together`);
  }

  const credentials = readCredentialFile();
  const password = credentials.shared_fixture_password;
  const tenantAdmin = credentials.tenant_admins?.[tenant];
  if (typeof password !== 'string' || !password || typeof tenantAdmin !== 'string') {
    throw new Error(`Credential file is missing shared_fixture_password or tenant_admins.${tenant}`);
  }

  if (!role) return { email: tenantAdmin, password };
  const separator = tenantAdmin.indexOf('@');
  if (separator < 1) throw new Error(`tenant_admins.${tenant} is not a valid email address`);
  return { email: `${role}@${tenantAdmin.slice(separator + 1)}`, password };
}
