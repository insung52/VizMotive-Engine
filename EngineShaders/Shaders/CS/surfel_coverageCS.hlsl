#define TEXTURE_SLOT_NONUNIFORM
#include "../Globals.hlsli"
#include "../ShaderInterop_SurfelGI.h"
#include "../CommonHF/raytracingHF.hlsli"
#include "../CommonHF/brdf.hlsli"

PUSHCONSTANT(push, SurfelDebugPushConstants);

StructuredBuffer<Surfel> surfelBuffer : register(t0);
StructuredBuffer<SurfelGridCell> surfelGridBuffer : register(t1);
StructuredBuffer<uint> surfelCellBuffer : register(t2);
Texture2D<float2> surfelMomentsTexture : register(t3);
Texture2D<uint> input_primitiveID_1 : register(t4);
Texture2D<uint> input_primitiveID_2 : register(t5);

RWStructuredBuffer<SurfelData> surfelDataBuffer : register(u0);
RWStructuredBuffer<uint> surfelDeadBuffer : register(u1);
RWStructuredBuffer<uint> surfelAliveBuffer : register(u2);
RWStructuredBuffer<SurfelStats> surfelStatsBuffer : register(u3);
RWTexture2D<float3> result : register(u4);
RWTexture2D<unorm float4> debugUAV : register(u5);

void write_result(uint2 DTid, float4 color)
{
	result[DTid] = color.rgb;
}
void write_debug(uint2 DTid, float4 debug)
{
	debugUAV[DTid * 2 + uint2(0, 0)] = debug;
	debugUAV[DTid * 2 + uint2(1, 0)] = debug;
	debugUAV[DTid * 2 + uint2(0, 1)] = debug;
	debugUAV[DTid * 2 + uint2(1, 1)] = debug;
}

groupshared uint GroupMinSurfelCount;

[numthreads(16, 16, 1)]
void main(uint3 DTid : SV_DispatchThreadID, uint groupIndex : SV_GroupIndex, uint3 Gid : SV_GroupID, uint3 GTid : SV_GroupThreadID)
{
	if (groupIndex == 0)
	{
		GroupMinSurfelCount = ~0;
	}
	GroupMemoryBarrierWithGroupSync();

	uint2 pixel = DTid.xy * 2;

	const float depth = texture_depth[pixel];
	if (depth == 0)
	{
		write_debug(DTid.xy, 0);
		return;
	}

	float4 debug = 0;
	float4 color = 0;

	float seed = GetFrame().time;
	RNG rng;
	rng.init(pixel, GetFrame().frame_count);

	const float2 uv = ((float2)pixel + 0.5) * GetCamera().internal_resolution_rcp;
	const float2 clipspace = uv_to_clipspace(uv);
	RayDesc ray = CreateCameraRay(clipspace);

	uint2 primitiveID = uint2(input_primitiveID_1[pixel], input_primitiveID_2[pixel]);
	if (!any(primitiveID))
	{
		write_debug(DTid.xy, 0);
		return;
	}

	PrimitiveID prim;
	prim.init();
	prim.unpack2(primitiveID);

	Surface surface;
	surface.init();
	if (!surface.load(prim, ray.Origin, ray.Direction))
	{
		return;
	}

	// FIX: VizMotive 의 compute_barycentrics 가 CCW winding mesh frontface 를 backface 로 잘못 판정.
	// raster visibility buffer 는 backface culling 이라 항상 frontface. N 강제 복원.
	if (surface.IsBackface())
	{
		surface.N = -surface.N;
		surface.facenormal = -surface.facenormal;
		surface.SetBackface(false);
	}

	const float3 N = surface.N;

	// SURFEL_DEBUG_SHADOW_TEST: 단계별 검증 (각 변수 시각화)
	// Stage A: light_count 시각화
	//   검정 = light_count == 0 (light buffer 비어있음!)
	//   회색 정도 = light_count / 5.0 (5개 light 면 흰색)
	//   파랑 (0,0,1) = light_count > 0 + NdotL > 0 (정상 진입)
	//   초록 (0,1,0) = + dist < range
	//   노랑 (1,1,0) = + shadow passed (light 도달)
	//   빨강 (1,0,0) = shadow blocked
	if (push.debug == SURFEL_DEBUG_SHADOW_TEST)
	{
		// N 정상 복원 확정. 이제 NEE 진단 활성.
		float4 sd_color = float4(0, 0, 0, 1);
		const uint light_count = lights().item_count();
		if (light_count == 0)
		{
			// light_count = 0. light buffer 비어있음. 검정 유지.
			write_debug(DTid.xy, float4(0.2, 0.2, 0.2, 1));  // 회색: light_count=0 marker
			return;
		}

		// stage marker R: light_count 시각화 (0~1)
		float lc_norm = saturate((float)light_count / 5.0);
		sd_color.r = lc_norm * 0.3;  // 작은 R base

		ShaderEntity light = load_entity(lights().first_item());
		float3 light_pos = light.position;
		float3 L = light_pos - surface.P;
		float dist2 = dot(L, L);
		float range = light.GetRange();
		float range2 = range * range;

		if (dist2 >= range2)
		{
			sd_color.rgb = float3(0.5, 0, 0.5);  // 마젠타: dist >= range
		}
		else
		{
			float dist = sqrt(dist2);
			L /= dist;
			float NdotL = dot(L, surface.N);

			if (NdotL <= 0)
			{
				sd_color.rgb = float3(0, 0, 0.5);  // 파랑: NdotL <= 0
			}
			else
			{
				RayDesc shadowRay;
				shadowRay.Origin = surface.P;
				shadowRay.TMin = 0.001;
				shadowRay.TMax = dist;
				shadowRay.Direction = L;

#ifdef RTAPI
				vzRayQuery sq;
				sq.TraceRayInline(
					scene_acceleration_structure,
					RAY_FLAG_SKIP_PROCEDURAL_PRIMITIVES |
					RAY_FLAG_FORCE_OPAQUE |
					RAY_FLAG_ACCEPT_FIRST_HIT_AND_END_SEARCH,
					0xFF,
					shadowRay
				);
				while (sq.Proceed());
				bool blocked = (sq.CommittedStatus() == COMMITTED_TRIANGLE_HIT);
				if (blocked)
					sd_color.rgb = float3(1, 0, 0);  // 빨강: shadow blocked
				else
					sd_color.rgb = float3(0, 1, 0);  // 초록: light reached!
#else
				sd_color.rgb = float3(0.5, 0.5, 0);  // RTAPI 비활성
#endif
			}
		}
		write_debug(DTid.xy, sd_color);
		return;
	}

	float coverage = 0;

	int3 gridpos = surfel_cell(surface.P);
	if (!surfel_cellvalid(gridpos))
	{
		write_debug(DTid.xy, 0);
		return;
	}

	uint cellindex = surfel_cellindex(gridpos);
	SurfelGridCell cell = surfelGridBuffer[cellindex];
	for (uint i = 0; i < cell.count; ++i)
	{
		uint surfel_index = surfelCellBuffer[cell.offset + i];
		Surfel surfel = surfelBuffer[surfel_index];

		float3 L = surface.P - surfel.position;
		float dist2 = dot(L, L);
		if (dist2 < sqr(surfel.GetRadius()))
		{
			float3 normal = normalize(unpack_half3(surfel.normal));
			float dotN = dot(N, normal);
			if (dotN > 0)
			{
				float dist = sqrt(dist2);
				float contribution = 1;

				contribution *= saturate(dotN);
				contribution *= saturate(1 - dist / surfel.GetRadius());
				contribution = smoothstep(0, 1, contribution);
				coverage += contribution;

				// pre_weight: moment_weight/life 적용 전 contribution. 진단 mode 에서 moment_weight=0 인 surfel 도 보이게 누적.
				float pre_weight = contribution;

				float2 moments = surfelMomentsTexture.SampleLevel(sampler_linear_clamp, surfel_moment_uv(surfel_index, normal, L / dist), 0);
				float moment_w = surfel_moment_weight(moments, dist);
				contribution *= moment_w;

				// contribution based on life can eliminate black popping surfels, but the surfel_data must be accessed...
				contribution = lerp(0, contribution, saturate(surfelDataBuffer[surfel_index].GetLife() / 2.0f));

				color += float4(SH::CalculateIrradiance(surfel.radiance.Unpack(), (half3)N), 1) * contribution;

				switch (push.debug)
				{
				case SURFEL_DEBUG_NORMAL:
					debug.rgb += normal * contribution;
					debug.a = 1;
					break;
				case SURFEL_DEBUG_RANDOM:
					debug += float4(random_color(surfel_index), 1) * contribution;
					break;
				case SURFEL_DEBUG_INCONSISTENCY:
					debug += float4(surfelDataBuffer[surfel_index].max_inconsistency.xxx, 1) * contribution;
					break;
				case SURFEL_DEBUG_LIFE:
					{
						float life_norm = saturate((float)surfelDataBuffer[surfel_index].GetLife() / 64.0f);
						float3 life_color = float3(1 - life_norm, life_norm, life_norm * 0.5);
						debug += float4(life_color, 1) * contribution;
					}
					break;
				case SURFEL_DEBUG_RAYCOUNT:
					{
						float ray_norm = saturate((float)surfelDataBuffer[surfel_index].GetRayCount() / 16.0f);
						float3 ray_color = float3(1 - ray_norm, ray_norm, ray_norm * 0.7);
						debug += float4(ray_color, 1) * contribution;
					}
					break;
				case SURFEL_DEBUG_MOMENT_WEIGHT:
					{
						// moment_w 자체 (0=검정, 1=흰색). pre_weight 로 누적해서 weight=0 인 surfel 도 검정으로 visible.
						debug.rgb += moment_w.xxx * pre_weight;
						debug.a += pre_weight;
					}
					break;
				case SURFEL_DEBUG_MEAN_DEPTH:
					{
						// moments.x (mean depth, 0~SURFEL_MAX_RADIUS=2). 0=검정, 2=흰색.
						float mean_norm = saturate(moments.x / SURFEL_MAX_RADIUS);
						debug.rgb += mean_norm.xxx * pre_weight;
						debug.a += pre_weight;
					}
					break;
				case SURFEL_DEBUG_RADIANCE_DC:
					{
						// surfel 자체 normal 방향의 irradiance (surface.N 무관). mean (radiance) freeze 직접 측정.
						float3 sh_irr = (float3)SH::CalculateIrradiance(surfel.radiance.Unpack(), (half3)normal);
						debug.rgb += sh_irr * pre_weight;
						debug.a += pre_weight;
					}
					break;
				default:
					break;
				}

			}

			if (push.debug == SURFEL_DEBUG_POINT)
			{
				if (dist2 <= sqr(0.05))
					debug = float4(1, 0, 1, 1);
			}
		}

	}

	if (cell.count < SURFEL_CELL_LIMIT)
	{
		uint surfel_count_at_pixel = 0;
		surfel_count_at_pixel |= (uint(coverage) & 0xFF) << 24; // the upper bits matter most for min selection
		surfel_count_at_pixel |= (uint(rng.next_float() * 65535) & 0xFFFF) << 8; // shuffle pixels randomly
		surfel_count_at_pixel |= (GTid.x & 0xF) << 4;
		surfel_count_at_pixel |= (GTid.y & 0xF) << 0;
		InterlockedMin(GroupMinSurfelCount, surfel_count_at_pixel);
	}

	if (color.a > 0)
	{
		color.rgb /= color.a;
		color.rgb /= PI;
		color.a = saturate(color.a);
	}

	switch (push.debug)
	{
	case SURFEL_DEBUG_NORMAL:
		debug.rgb = normalize(debug.rgb) * 0.5 + 0.5;
		break;
	case SURFEL_DEBUG_COLOR:
		debug = color;
		debug.rgb = tonemap(debug.rgb);
		debug.a = 1;
		break;
	case SURFEL_DEBUG_RANDOM:
		if (debug.a > 0)
		{
			debug /= debug.a;
		}
		else
		{
			debug = 0;
		}
		break;
	case SURFEL_DEBUG_HEATMAP:
		{
			const float3 mapTex[] = {
				float3(0,0,0),
				float3(0,0,1),
				float3(0,1,1),
				float3(0,1,0),
				float3(1,1,0),
				float3(1,0,0),
			};
			const uint mapTexLen = 5;
			const uint maxHeat = 100;
			float l = saturate((float)cell.count / maxHeat) * mapTexLen;
			float3 a = mapTex[floor(l)];
			float3 b = mapTex[ceil(l)];
			float4 heatmap = float4(lerp(a, b, l - floor(l)), 0.8);
			debug = heatmap;
		}
		break;
	case SURFEL_DEBUG_INCONSISTENCY:
		if (debug.a > 0)
		{
			debug /= debug.a;
		}
		else
		{
			debug = 0;
		}
		break;
	case SURFEL_DEBUG_LIFE:
		if (debug.a > 0)
		{
			debug /= debug.a;
		}
		else
		{
			debug = 0;
		}
		break;
	case SURFEL_DEBUG_RAYCOUNT:
		if (debug.a > 0)
		{
			debug /= debug.a;
		}
		else
		{
			debug = 0;
		}
		break;
	case SURFEL_DEBUG_MOMENT_WEIGHT:
		if (debug.a > 0)
		{
			debug.rgb /= debug.a;
			debug.a = 1;
		}
		else
		{
			debug = 0;
		}
		break;
	case SURFEL_DEBUG_MEAN_DEPTH:
		if (debug.a > 0)
		{
			debug.rgb /= debug.a;
			debug.a = 1;
		}
		else
		{
			debug = 0;
		}
		break;
	case SURFEL_DEBUG_RADIANCE_DC:
		if (debug.a > 0)
		{
			debug.rgb /= debug.a;
			debug.rgb = tonemap(debug.rgb);
			debug.a = 1;
		}
		else
		{
			debug = 0;
		}
		break;
	default:
		break;
	}

	GroupMemoryBarrierWithGroupSync();

	if (cell.count < SURFEL_CELL_LIMIT)
	{
		uint surfel_coverage = GroupMinSurfelCount;
		uint2 minGTid;
		minGTid.x = (surfel_coverage >> 4) & 0xF;
		minGTid.y = (surfel_coverage >> 0) & 0xF;
		uint coverage_amount = surfel_coverage >> 24;
		if (GTid.x == minGTid.x && GTid.y == minGTid.y && coverage < SURFEL_TARGET_COVERAGE)
		{
			// Slow down the propagation by chance
			//	Closer surfaces have less chance to avoid excessive clumping of surfels
			const float lineardepth = compute_lineardepth(depth) * GetCamera().z_far_rcp;
			const float chance = pow(1 - lineardepth, 8);

			if (rng.next_float() < chance)
				return;

			// new particle index retrieved from dead list (pop):
			int deadCount;
			InterlockedAdd(surfelStatsBuffer[0].deadCount, -1, deadCount);
			if (deadCount <= 0 || deadCount > SURFEL_CAPACITY)
				return;
			uint newSurfelIndex = surfelDeadBuffer[deadCount - 1];

			// and add index to the alive list (push):
			uint aliveCount;
			InterlockedAdd(surfelStatsBuffer[0].nextCount, 1, aliveCount);
			if (aliveCount < SURFEL_CAPACITY)
			{
				surfelAliveBuffer[aliveCount] = newSurfelIndex;

				SurfelData surfel_data = (SurfelData)0;
				surfel_data.primitiveID = prim.pack2();
				surfel_data.bary = pack_half2(surface.bary.xy);
				surfel_data.uid = surface.inst.uid;
				surfel_data.SetBackfaceNormal(surface.IsBackface());
				surfel_data.max_inconsistency = 1;
				surfelDataBuffer[newSurfelIndex] = surfel_data;
			}
		}
	}

	write_result(DTid.xy, color);
	write_debug(DTid.xy, debug);
}
