(define (problem blocksworld)
	(:domain blocksworld)
	(:objects
		blue - block
		green - block
		orange - block
		purple - block
		red - block
		yellow - block
		robot - robot
	)
	(:init (handempty robot)
		(ontable red)
		(on yellow red)
		(clear yellow)
		(ontable purple)
		(on orange purple)
		(clear orange)

		(ontable green)
		(on blue green)
		(clear blue)
	)
	(:goal (and (handempty robot)
		(ontable purple)
		(on green purple)
		(clear green)

		(ontable red)
		(clear red)
		(ontable orange)
		(clear orange)
		(ontable yellow)
		(clear yellow)
		(ontable blue)
		(clear blue)
	))
)