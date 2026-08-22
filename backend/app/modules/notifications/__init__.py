"""Notificaciones — C-06, `T-035`.

Dos canales con garantias distintas: in-app es transaccional y es el canal de
registro; el email es mejor-esfuerzo y no se reintenta.

⚠️ **Sin superficie HTTP, y no es un olvido.** `ADR-024` no define ninguna celda
de `notifications` en la matriz RBAC. Escribir `GET /notifications` obligaria a
inventar quien puede leerlas, que es una decision de autorizacion implicita — y
el principio 5 las declara no vinculantes. La celda va al ADR antes que el
endpoint.
"""
