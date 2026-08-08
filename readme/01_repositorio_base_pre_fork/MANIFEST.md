# Manifest del repositorio base pre-fork

## Origen

- Commit de origen: `595989d`
- Archivo de origen: `README.md`
- Snapshot creado: 2026-08-08
- Destino: `readme/01_repositorio_base_pre_fork/README.md`

## Regla de preservacion

El README conserva el contenido del archivo de origen. La unica transformacion aplicada fue
corregir los enlaces relativos para que sigan funcionando desde esta carpeta anidada:

| Enlace en la raiz | Enlace en el snapshot |
|---|---|
| `docs/rubrica-evaluacion.md` | `../../docs/rubrica-evaluacion.md` |
| `docs/stack-tecnico.md` | `../../docs/stack-tecnico.md` |
| `dataset/` | `../../dataset/` |
| `LICENSE` | `../../LICENSE` |

No se copian `dataset/` ni los documentos canonicos de `docs/`; el snapshot solo conserva el
README del repositorio base y apunta a esas fuentes mediante enlaces.

## Verificacion

Desde la raiz del repositorio, comparar el snapshot con el contenido del commit y revisar
solo las rutas listadas arriba:

```text
git show 595989d:README.md
```

La comprobacion de igualdad debe ignorar unicamente el prefijo relativo de esos enlaces.
No se debe editar el snapshot para incorporar cambios posteriores del README actual sin
crear un nuevo manifest y una nueva referencia de origen.
