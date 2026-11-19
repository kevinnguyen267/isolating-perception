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
		(ontable orange)
		(clear orange)
		(ontable blue)
		(on green blue)
		(clear green)

		(ontable purple)
		(on red purple)
		(on yellow red)
		(clear yellow)
	)
	(:goal (and (handempty robot)
		(ontable orange)
		(clear orange)
		(ontable red)
		(clear red)
		(ontable green)
		(on purple green)
		(clear purple)

		(ontable blue)
		(on yellow blue)
		(clear yellow)
	))
)