import { ApiError } from "./api/client";
import { serverApiRequest } from "./api/server";
import type { ProductResponse } from "./api/generated";
import type { ProductDetailViewModel } from "./api/view-models";

export async function getProductDetail(id: string) {
  try {
    const data = await serverApiRequest<ProductResponse>(`/api/v1/products/${encodeURIComponent(id)}`);
    const product: ProductDetailViewModel = { id: data.id, name: data.name, sku: data.internal_sku, marketplace: undefined, organization_id: data.organization_id, group_id: data.group_id, brand: data.brand, category: data.category };
    return { data: product };
  } catch (error) {
    return { error: error instanceof ApiError ? error : new ApiError("Не удалось загрузить карточку товара", 500) };
  }
}
