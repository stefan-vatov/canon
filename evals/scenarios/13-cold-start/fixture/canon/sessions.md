# Sessions

A logout revokes the session on the server before the client clears its cookie,
so a copied cookie stops working at once. Token refresh never extends a session
past its absolute lifetime; the user signs in again.
