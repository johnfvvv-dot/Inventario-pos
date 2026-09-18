def info_productos(*precios: int, **kwargs) -> dict:
    """Calcula el total de productos y aplica un descuento opcional."""
    if not precios:
        raise ValueError("Debes ingresar al menos un precio.")

    total = sum(precios)
    resultado = {
        "subtotal": total,
        "descuento_porcentaje": 0,
        "monto_descuento": 0,
        "total_final": total,
    }

    print(f"Precio total de los productos: {total}")

    descuento = kwargs.get("descuento")

    if descuento is None:
        print("No hay descuento")
        return resultado

    if not 0 <= descuento <= 100:
        raise ValueError("El descuento debe estar entre 0 y 100.")

    monto_descuento = total * descuento / 100
    total_con_descuento = total - monto_descuento

    resultado.update({
        "descuento_porcentaje": descuento,
        "monto_descuento": monto_descuento,
        "total_final": total_con_descuento,
    })

    print(
        f"Tu descuento es de {descuento}%, "
        f"el total es de {total_con_descuento}"
    )
    return resultado


if __name__ == "__main__":
    venta = info_productos(
        23000, 56000, 46000, 32000, 78000, 12000,
        descuento=15,
    )
    print(f"Resumen: {venta}")
