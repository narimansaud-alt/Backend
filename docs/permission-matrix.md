# Organization permission matrix

System administrators retain the existing global auth behavior. Organization
roles below are scoped to one organization. An explicit user permission can
narrow a role, but cannot broaden cabinet assignment.

| Permission | Owner | Admin | Manager | Viewer |
|---|:---:|:---:|:---:|:---:|
| `organization:view` | ✓ | ✓ | ✓ | ✓ |
| `organization:manage` | ✓ | ✓ | — | — |
| `member:view` | ✓ | ✓ | ✓ | — |
| `member:invite` | ✓ | ✓ | — | — |
| `member:manage` | ✓ | ✓ | — | — |
| `cabinet:view` | all | all | assigned | assigned |
| `cabinet:manage` | ✓ | ✓ | — | — |
| `cabinet:sync` | ✓ | ✓ | assigned | — |
| `analytics:view` | all | all | assigned | assigned |
| `analytics:export` | ✓ | ✓ | assigned | — |
| `cost:manage` | ✓ | ✓ | assigned | — |
| `finance:manage` | ✓ | ✓ | — | — |
| `plan:manage` | ✓ | ✓ | assigned | — |

Owners cannot be removed or demoted through the ordinary member endpoint.
Owner/admin-only operations require both the role and organization membership;
a global permission string alone never grants access to a foreign organization.

